import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime

from lib import utils
from lib.constants import EVENT_TYPES_JSON_FILE_PATH


class GenerateHTML:
    TEMP_WEB_FOLDER = "data/tmp/web"
    INDEX_TEMPLATE_HTML_FILE_PATH = "web/index_template.html"
    INDEX_GENERATED_HTML_FILE_PATH = os.path.join(TEMP_WEB_FOLDER, "index.html")
    CRAWLER_STATUS_INFO_JSON_FILE = "data/tmp/crawler_status_info.json"
    CRAWLER_STATUS_TEMPLATE_HTML_FILE_PATH = "web/crawler_status_template.html"
    CRAWLER_STATUS_GENERATED_HTML_FILE_PATH = os.path.join(TEMP_WEB_FOLDER, "crawler_status.html")
    FALLBACK_EVENT_TYPE = "ostatní"

    def __init__(self) -> None:
        self.connection = utils.create_connection()
        self.latest_execution_log_path = self._get_latest_execution_log_path()

        missing_views = utils.check_db_views(self.connection, ["event_data_view"])
        if len(missing_views) != 0:
            raise Exception("Missing views in the DB: {}".format(missing_views))

    def run(self) -> None:
        print("Generating HTML...", end="")
        events_dataset = self.get_events()
        self.complete_index_template(events_dataset)
        status_info = self.get_crawler_status_info()
        self.complete_crawler_status_template(status_info)
        self.copy_other_files()
        print("DONE")

    def get_events(self) -> dict:
        query = '''
                    SELECT calendar__url, calendar__downloaded_at,
                           event_url__url,
                           event_data__id, event_data__title, event_data__perex, event_data__location, event_data__gps, event_data__organizer, event_data__types,
                           event_data_datetime__start_date, event_data_datetime__start_time, event_data_datetime__end_date, event_data_datetime__end_time,
                           event_data_gps__online, event_data_gps__has_default, event_data_gps__gps, event_data_gps__location, event_data_gps__municipality, event_data_gps__district,
                           event_data_keywords__keyword,
                           event_data_types__type
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL 
                      AND (event_data_datetime__start_date >= date('now') OR (event_data_datetime__end_date IS NOT NULL AND event_data_datetime__end_date >= date('now')))
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                '''

        cursor = self.connection.execute(query)
        events_tuples = cursor.fetchall()

        calendars_with_default_location_base = utils.get_base_dict_per_url(utils.get_base_with_default_location())
        calendars_with_default_location = {}
        for calendar_url, calendar_base in calendars_with_default_location_base.items():
            calendars_with_default_location[calendar_url] = calendar_base['default_location']

        event_ids_list = set()
        events_dataset = dict()
        for event in events_tuples:
            event_id = event[3]
            event_ids_list.add(event_id)

            calendar_url = event[0]
            if calendar_url in calendars_with_default_location:
                default_location = calendars_with_default_location[calendar_url]
            else:
                default_location = event[17]
            start_date, start_time, end_date, end_time = event[10], event[11], event[12], event[13]
            datetime_tuple = (start_date, start_time, end_date, end_time) if start_date else None

            if event_id in events_dataset:
                if event[21]:
                    events_dataset[event_id]['types'].add(event[21])
                if event[20]:
                    events_dataset[event_id]['keywords'].add(event[20])
                if datetime_tuple:
                    events_dataset[event_id]['datetimes'].add(datetime_tuple)
            else:
                events_dataset[event_id] = {
                    "event_url": event[2],
                    "title": utils.sanitize_string_for_html(event[4]),
                    "perex": utils.sanitize_string_for_html(event[5]),
                    "location": utils.sanitize_string_for_html(event[6]),
                    "gps": event[7],
                    "organizer": utils.sanitize_string_for_html(event[8]),
                    "types": {event[21]} if event[21] else set(),
                    "keywords": {event[20]} if event[20] else set(),
                    "datetimes": {datetime_tuple} if datetime_tuple else set(),
                    "online": event[14] == 1,
                    "has_default": event[15] == 1,
                    "geocoded_gps": event[16],
                    "default_location": default_location,
                    "municipality": event[18],
                    "district": event[19],
                    "calendar_url": calendar_url,
                    "calendar_downloaded_at": event[1]
                }

        for event_id in events_dataset:
            types_list = events_dataset[event_id]['types']
            events_dataset[event_id]['types'] = list(sorted(self._get_associated_types(types_list), key=str.lower))
            events_dataset[event_id]['keywords'] = list(sorted(events_dataset[event_id]['keywords'], key=str.lower))
            events_dataset[event_id]['datetimes'] = list(events_dataset[event_id]['datetimes'])

        return events_dataset

    @staticmethod
    def _prepare_types() -> dict:
        with open(EVENT_TYPES_JSON_FILE_PATH, 'r') as types_file:
            types_list = json.load(types_file)

        types_graph = defaultdict(set)
        for type_dict in types_list:
            main_type = type_dict['type']
            supertypes = type_dict.get('supertypes', [])
            types_graph[main_type].update(supertypes)

        def add_supertypes_rec(type_word: str) -> set:
            out = {type_word}
            if type_word in types_graph:
                for supertype in types_graph[type_word]:
                    out.update(add_supertypes_rec(supertype))
            return out

        types_mapping = defaultdict(set)
        for type_dict in types_list:
            main_type = type_dict['type']
            types_mapping[main_type] = add_supertypes_rec(main_type)

        return {key: list(value) for key, value in types_mapping.items()}

    def _get_associated_types(self, types: set) -> list:
        mapping_types = self._prepare_types()
        mapped_types = set()
        for event_type in types:
            mapped_types.update(mapping_types[event_type])
        if len(mapped_types) == 0:
            return [GenerateHTML.FALLBACK_EVENT_TYPE]
        else:
            return list(mapped_types)

    @staticmethod
    def _get_types_and_keywords(input_events: dict) -> (list, list):
        types = set()
        keywords = set()

        for event_id in input_events:
            types.update(input_events[event_id]["types"])
            keywords.update(input_events[event_id]["keywords"])

        return sorted(list(types), key=str.lower), sorted(list(keywords), key=str.lower)

    def complete_index_template(self, events_dataset: dict) -> None:
        with open(GenerateHTML.INDEX_TEMPLATE_HTML_FILE_PATH, 'r') as index_template_file:
            file = index_template_file.read()

        data = json.dumps(events_dataset, indent=4, ensure_ascii=True)
        file = file.replace('{{events_dataset}}', data)

        event_types, event_keywords = self._get_types_and_keywords(events_dataset)
        event_types_data = json.dumps(event_types, indent=4, ensure_ascii=True)
        file = file.replace('{{event_types}}', event_types_data)
        event_keywords_data = json.dumps(event_keywords, indent=4, ensure_ascii=True)
        file = file.replace('{{event_keywords}}', event_keywords_data)

        calendar_sources_modal, calendars_count = self._get_calendar_sources_modal()
        file = file.replace('{{calendar_sources_count}}', str(calendars_count))
        file = file.replace('{{calendar_sources}}', calendar_sources_modal)

        os.makedirs(GenerateHTML.TEMP_WEB_FOLDER, exist_ok=True)
        with open(GenerateHTML.INDEX_GENERATED_HTML_FILE_PATH, 'w') as index_generated_file:
            index_generated_file.write(file)

    @staticmethod
    def _get_calendar_sources_modal() -> (str, int):
        active_base = utils.get_active_base()
        parsers = {}
        calendars_count = 0
        for calendar in active_base:
            calendars_count += 1
            if calendar['parser'] in parsers:
                parsers[calendar['parser']]['count'] += 1
                parsers[calendar['parser']]['calendars'].append(calendar['url'])
            else:
                parsers[calendar['parser']] = {
                    'count': 1,
                    'calendars': [calendar['url']]
                }
        calendar_sources_modal = ""
        for parser in parsers:
            if parsers[parser]['count'] > 1:
                header_string = "<i class=\"fa fa-caret-down\"></i> {} <i>({})</i>".format(parser, str(
                    parsers[parser]['count']))
                href = "#collapse-parser-{}".format(parser)
                click = "data-toggle=\"collapse\""
            else:
                header_string = parsers[parser]['calendars'][0]
                href = parsers[parser]['calendars'][0]
                click = "target=\"_blank\""
            calendar_card = "<div id=\"heading-parser-{}\" class=\"card-header\" style=\"padding: 0;\">\n" \
                            "  <h5 class=\"mb-0\">\n" \
                            "      <a class=\"btn btn-link\" role=\"button\"" \
                            "               href=\"{}\" {}" \
                            "              aria-expanded=\"true\" aria-controls=\"collapse-parser-{}\">" \
                            "          {}\n" \
                            "      </a>\n" \
                            "  </h5>\n" \
                            "</div>\n".format(parser, href, click, parser, header_string)
            if parsers[parser]['count'] > 1:
                calendars_list = ""
                for calendar in parsers[parser]['calendars']:
                    calendars_list += "<li class=\"list-group-item list-group-item-action\" " \
                                      "    onclick=\"window.open('{}', '_blank');\">\n" \
                                      "     <a href=\"#\">{}</a>\n" \
                                      "</li>".format(calendar, calendar)
                calendar_card += "<div id=\"collapse-parser-{}\" class=\"collapse\" " \
                                 "     aria-labelledby=\"heading-parser-{}\" data-parent=\"#accordion\">\n" \
                                 "  <div class=\"card-body\">\n" \
                                 "      <ul class=\"list-group\">\n" \
                                 "          {}\n" \
                                 "      </ul>\n" \
                                 "  </div>\n" \
                                 "</div>\n".format(parser, parser, calendars_list)
            calendar_card = "<div class=\"card\">{}</div>\n".format(calendar_card)
            calendar_sources_modal += calendar_card

        return calendar_sources_modal, calendars_count

    @staticmethod
    def get_crawler_status_info() -> dict:
        with open(GenerateHTML.CRAWLER_STATUS_INFO_JSON_FILE, 'r') as status_json_file:
            crawler_status_dict = json.load(status_json_file)

        return crawler_status_dict

    def complete_crawler_status_template(self, status_info: dict) -> None:
        with open(GenerateHTML.CRAWLER_STATUS_TEMPLATE_HTML_FILE_PATH, 'r') as crawler_status_template_file:
            file = crawler_status_template_file.read()
        file = file.replace('{{all_events_count}}', str(status_info['statistics']['total_count'])) \
            .replace('{{future_events_count}}', str(status_info['statistics']['future_count'])) \
            .replace('{{calendars_data}}', json.dumps(status_info['calendars'], indent=4, ensure_ascii=True)) \
            .replace('{{events_data}}', json.dumps(status_info['events'], indent=4, ensure_ascii=True)) \
            .replace('{{events_per_week}}',
                     json.dumps(status_info['statistics']['count_per_week'], indent=4, ensure_ascii=True)) \
            .replace('{{events_per_calendar}}',
                     json.dumps(status_info['statistics']['count_per_calendar'], indent=4, ensure_ascii=True)) \
            .replace('{{events_per_parser}}',
                     json.dumps(status_info['statistics']['count_per_parser'], indent=4, ensure_ascii=True)) \
            .replace('{{failing_calendars}}',
                     json.dumps(status_info['failures']['failed_calendars'], indent=4, ensure_ascii=True)) \
            .replace('{{empty_calendars}}',
                     json.dumps(status_info['failures']['empty_calendars'], indent=4, ensure_ascii=True)) \
            .replace('{{calendars_with_failed_events}}',
                     json.dumps(status_info['failures']['failure_percentage_per_calendar'],
                                indent=4, ensure_ascii=True)) \
            .replace('{{failed_events}}',
                     json.dumps(status_info['failures']['failed_events_errors'], indent=4, ensure_ascii=True))

        per_day_table_tbody = ""
        for item in status_info['statistics']['count_per_day']:
            per_day_table_tbody += "<tr>\n" \
                                   "\t<td>{}</td>\n" \
                                   "\t<td>{}</td>\n" \
                                   "</tr>\n".format(item['day'], str(item['count']))
        file = file.replace('{{counts_per_day}}', per_day_table_tbody)

        base_name = os.path.basename(self.latest_execution_log_path)
        datetime_str = re.search(r'^cron_process_([\d\-_]*).txt$', base_name).group(1)
        datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%d_%H-%M-%S')
        file = file.replace('{{latest_execution_datetime}}', datetime.strftime(datetime_obj, '%d %B %Y %H:%M'))

        os.makedirs(GenerateHTML.TEMP_WEB_FOLDER, exist_ok=True)
        with open(GenerateHTML.CRAWLER_STATUS_GENERATED_HTML_FILE_PATH, 'w') as crawler_status_generated_file:
            crawler_status_generated_file.write(file)

    def copy_other_files(self) -> None:
        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/'), exist_ok=True)
        shutil.copy2('web/scripts/events_map.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/events_map.js'))
        shutil.copy2('web/scripts/index.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/index.js'))
        shutil.copy2('web/scripts/datetime_pickers.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/datetime_pickers.js'))
        shutil.copy2('web/scripts/crawler_status.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/crawler_status.js'))
        shutil.copy2('web/scripts/statistics_graphs.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/statistics_graphs.js'))
        shutil.copy2('web/scripts/localization.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/localization.js'))

        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/'), exist_ok=True)
        shutil.copy2('web/styles/global.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/global.css'))
        shutil.copy2('web/styles/index.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/index.css'))
        shutil.copy2('web/styles/crawler_status.css',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/crawler_status.css'))

        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'assets/'), exist_ok=True)
        shutil.copy2(self.latest_execution_log_path,
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'assets/execution_log.txt'))
        shutil.copy2('data/tmp/geocode_location_output.json',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'assets/geocoding_log.json'))

    @staticmethod
    def _get_latest_execution_log_path() -> str:
        logs_paths = [os.path.join('data/log', basename) for basename in os.listdir('data/log')]
        return max(logs_paths, key=os.path.getctime)


if __name__ == '__main__':
    generate_html = GenerateHTML()
    generate_html.run()
