import json
import os
import shutil

from lib import utils


class GenerateHTML:
    INDEX_TEMPLATE_HTML_FILE_PATH = "web/index_template.html"
    TEMP_WEB_FOLDER = "data/tmp/web"
    INDEX_GENERATED_HTML_FILE_PATH = os.path.join(TEMP_WEB_FOLDER, "index.html")

    def __init__(self):
        self.connection = utils.create_connection()

        missing_views = utils.check_db_views(self.connection, ["event_data_view"])
        if len(missing_views) != 0:
            raise Exception("Missing views in the DB: {}".format(missing_views))

    def run(self):
        events = self.get_events()

        with open(GenerateHTML.INDEX_TEMPLATE_HTML_FILE_PATH, 'r') as template_html_file:
            file = template_html_file.read()
            data = json.dumps(events, indent=4, ensure_ascii=True)
            file = file.replace('<<events_dataset>>', data)

        os.makedirs(GenerateHTML.TEMP_WEB_FOLDER, exist_ok=True)
        with open(GenerateHTML.INDEX_GENERATED_HTML_FILE_PATH, 'w') as generated_html_file:
            generated_html_file.write(file)

        # Copy Scripts
        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/'), exist_ok=True)
        shutil.copy2('web/scripts/events_map.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/events_map.js'))
        shutil.copy2('web/scripts/index.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/index.js'))
        shutil.copy2('web/scripts/datetime_pickers.js', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'scripts/datetime_pickers.js'))

        # Copy Styles
        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/'), exist_ok=True)
        shutil.copy2('web/styles/dashboard.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/dashboard.css'))
        shutil.copy2('web/styles/index.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/index.css'))

    def get_events(self):
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

        events_jsons = {}
        for event in events_tuples:
            event_id = event[3]
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
                "default_location": event[17],
                "municipality": event[18],
                "district": event[19],
                "calendar_url": event[0],
                "calendar_downloaded_at": event[1]
            }
            events_jsons[event_id] = event_dict

        return events_jsons

    @staticmethod
    def sanitize_string(input_string):
        if not input_string:
            return None
        return input_string.replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"').replace('`', '\'')


if __name__ == '__main__':
    generate_html = GenerateHTML()
    generate_html.run()
