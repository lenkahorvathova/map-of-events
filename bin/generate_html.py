import json
import os
import shutil
from typing import Optional

from lib import utils


class GenerateHTML:
    TEMP_WEB_FOLDER = "data/tmp/web"
    INDEX_TEMPLATE_HTML_FILE_PATH = "web/index_template.html"
    INDEX_GENERATED_HTML_FILE_PATH = os.path.join(TEMP_WEB_FOLDER, "index.html")
    CRAWLER_STATUS_INFO_JSON_FILE = "data/tmp/crawler_status_info.json"
    CRAWLER_STATUS_TEMPLATE_HTML_FILE_PATH = "web/crawler_status_template.html"
    CRAWLER_STATUS_GENERATED_HTML_FILE_PATH = os.path.join(TEMP_WEB_FOLDER, "crawler_status.html")

    def __init__(self) -> None:
        self.connection = utils.create_connection()

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
                           event_data_gps__online, event_data_gps__has_default, event_data_gps__gps, event_data_gps__location, event_data_gps__municipality, event_data_gps__district
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL 
                      AND (event_data_datetime__start_date >= date('now') OR (event_data_datetime__end_date IS NOT NULL AND event_data_datetime__end_date >= date('now')))
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                '''

        cursor = self.connection.execute(query)
        events_tuples = cursor.fetchall()

        calendars_with_default_location = {}
        for calendar in utils.get_base_with_default_location():
            calendars_with_default_location[calendar['url']] = calendar['default_location']

        events_dataset = {}
        for event in events_tuples:
            event_id = event[3]
            calendar_url = event[0]
            event_dict = {
                "event_url": event[2],
                "title": self.sanitize_string(event[4]),
                "perex": self.sanitize_string(event[5]),
                "location": self.sanitize_string(event[6]),
                "gps": event[7],
                "organizer": self.sanitize_string(event[8]),
                "types": json.loads(event[9]) if event[9] else [],
                "start_date": event[10],
                "start_time": event[11],
                "end_date": event[12],
                "end_time": event[13],
                "online": event[14] == 1,
                "has_default": event[15] == 1,
                "geocoded_gps": event[16],
                "default_location": calendars_with_default_location[calendar_url]
                if calendar_url in calendars_with_default_location
                else event[17],
                "municipality": event[18],
                "district": event[19],
                "calendar_url": calendar_url,
                "calendar_downloaded_at": event[1]
            }
            events_dataset[event_id] = event_dict

        return events_dataset

    @staticmethod
    def sanitize_string(input_string: str) -> Optional[str]:
        if not input_string:
            return None
        return input_string.replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"').replace('`', '\'')

    @staticmethod
    def complete_index_template(events_dataset: dict) -> None:
        with open(GenerateHTML.INDEX_TEMPLATE_HTML_FILE_PATH, 'r') as index_template_file:
            file = index_template_file.read()
            data = json.dumps(events_dataset, indent=4, ensure_ascii=True)
            file = file.replace('{{events_dataset}}', data)

        os.makedirs(GenerateHTML.TEMP_WEB_FOLDER, exist_ok=True)
        with open(GenerateHTML.INDEX_GENERATED_HTML_FILE_PATH, 'w') as index_generated_file:
            index_generated_file.write(file)

    @staticmethod
    def get_crawler_status_info() -> dict:
        with open(GenerateHTML.CRAWLER_STATUS_INFO_JSON_FILE, 'r') as status_json_file:
            crawler_status_dict = json.load(status_json_file)

        return crawler_status_dict

    @staticmethod
    def complete_crawler_status_template(status_info: dict) -> None:
        with open(GenerateHTML.CRAWLER_STATUS_TEMPLATE_HTML_FILE_PATH, 'r') as crawler_status_template_file:
            file = crawler_status_template_file.read()
        file = file.replace('{{all_events_count}}', str(status_info['statistics']['total_count'])) \
            .replace('{{future_events_count}}', str(status_info['statistics']['future_count'])) \
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

        os.makedirs(GenerateHTML.TEMP_WEB_FOLDER, exist_ok=True)
        with open(GenerateHTML.CRAWLER_STATUS_GENERATED_HTML_FILE_PATH, 'w') as crawler_status_generated_file:
            crawler_status_generated_file.write(file)

    @staticmethod
    def copy_other_files() -> None:
        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/'), exist_ok=True)
        shutil.copy2('web/scripts/events_map.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/events_map.js'))
        shutil.copy2('web/scripts/index.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/index.js'))
        shutil.copy2('web/scripts/datetime_pickers.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/datetime_pickers.js'))
        shutil.copy2('web/scripts/crawler_status.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/crawler_status.js'))
        shutil.copy2('web/scripts/statistics_graphs.js',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/statistics_graphs.js'))

        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/'), exist_ok=True)
        shutil.copy2('web/styles/dashboard.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/dashboard.css'))
        shutil.copy2('web/styles/index.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/index.css'))
        shutil.copy2('web/styles/crawler_status.css',
                     os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/crawler_status.css'))


if __name__ == '__main__':
    generate_html = GenerateHTML()
    generate_html.run()
