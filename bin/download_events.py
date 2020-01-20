import json
import os
from urllib.parse import urljoin

from lxml import etree

from lib.constants import DATA_DIR_PATH
from lib.utils import create_connection, load_base, get_xpaths, download_html_content


class DownloadEvents:
    """ Downloads an HTML content of an events' pages parsed from a calendar pages
        and stores event's URL, HTML file path and timestamp of a download into the database.

    Outputs a json file with the download info about most recent run of the script.
    """

    OUTPUT_FILE_PATH = "data/tmp/download_events_output.json"
    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.connection = create_connection()
        self.base_dict = load_base()

    def run(self) -> None:
        input_urls = self.load_input_urls()
        events_to_insert, log_info = self.download_events(input_urls)
        self.store_to_database(events_to_insert)
        self.store_results(log_info)

    def load_input_urls(self) -> list:
        with self.connection:
            cursor = self.connection.execute('''SELECT url FROM websites''')
            return [url[0] for url in cursor.fetchall()]

    def download_events(self, input_urls: list) -> (list, list):
        events_to_insert = []
        log_info = []

        for website in input_urls:
            website_events_to_insert, website_log_obj = self.process_website(website)

            events_to_insert.extend(website_events_to_insert)
            log_info.append(website_log_obj)

        return events_to_insert, log_info

    def process_website(self, url: str) -> (list, dict):
        base = self.get_website_base(url)
        domain = base["domain"]

        events_to_insert = []
        website_log_obj = {
            "domain": domain,
            "files": []
        }

        xpaths = get_xpaths(base["parser"])
        current_dir = os.path.join(DATA_DIR_PATH, domain)

        for filename in os.listdir(current_dir):
            file_log_obj = {
                "name": filename,
                "events_list": []
            }

            with open(os.path.join(current_dir, filename)) as html_file:
                dom = etree.parse(html_file, etree.HTMLParser())
                root = dom.xpath(xpaths["root"])[0]

                for el in root.xpath(xpaths["url"]):
                    event_url = urljoin(url, el)

                    html_file_dir = os.path.join(DATA_DIR_PATH, domain, DownloadEvents.EVENTS_FOLDER_NAME)
                    info_to_insert = download_html_content(event_url, html_file_dir)

                    if info_to_insert:
                        events_to_insert.append(info_to_insert)

                    file_log_obj["events_list"].append(event_url)

                file_log_obj["events_count"] = len(file_log_obj["events_list"])

            website_log_obj["files"].append(file_log_obj)

        return events_to_insert, website_log_obj

    def get_website_base(self, url: str) -> dict:
        for obj in self.base_dict:
            if obj['url'] == url:
                return obj

    def store_to_database(self, events_to_insert: list) -> None:
        with self.connection:
            for event_info in events_to_insert:
                url, html_file_path = event_info

                sql_command = '''
                        INSERT INTO events_raw(url, html_file_path)
                        VALUES(?, ?)
                    '''
                values = (url, html_file_path)

                self.connection.execute(sql_command, values)

            self.connection.commit()

    @staticmethod
    def store_results(log_info: list) -> None:
        with open(DownloadEvents.OUTPUT_FILE_PATH, 'w') as output_file:
            output_file.write(json.dumps(log_info, indent=4))


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
