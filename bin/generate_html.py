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

        # Copy Styles
        os.makedirs(os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/'), exist_ok=True)
        shutil.copy2('web/styles/dashboard.css', os.path.join(GenerateHTML.TEMP_WEB_FOLDER, 'styles/dashboard.css'))

    def get_events(self):
        query = '''SELECT ed.id, ed.title, ed.perex, ed.location, ed.organizer, ed.types, 
                          edd.start_date, edd.start_time, edd.end_date, edd.end_time,
                          edg.online, edg.has_default, edg.gps, edg.municipality, edg.district
                   FROM event_data ed 
                   INNER JOIN event_data_datetime edd ON ed.id == edd.event_data_id 
                   INNER JOIN event_data_gps edg ON ed.id == edg.event_data_id 
                   WHERE  edd.start_date IS NOT NULL AND edd.start_date >= date('now')
                   AND (edg.gps IS NOT NULL OR edg.online == 1);'''

        cursor = self.connection.execute(query)
        events_tuples = cursor.fetchall()

        events_jsons = {}
        for event in events_tuples:
            event_id = event[0]
            event_dict = {
                "title": self.sanitize_string(event[1]),
                "perex": self.sanitize_string(event[2]),
                "location": self.sanitize_string(event[3]),
                "organizer": self.sanitize_string(event[4]),
                "types": json.loads(event[5]) if event[5] else [],
                "start_date": event[6],
                "start_time": event[7],
                "end_date": event[8],
                "end_time": event[9],
                "online": event[10] == 1,
                "has_default": event[11] == 1,
                "gps": event[12],
                "municipality": event[13],
                "district": event[14]
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
