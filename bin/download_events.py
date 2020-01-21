import os
import urllib.parse as urllib

from lxml import etree

from lib import utils
from lib.constants import DATA_DIR_PATH


class DownloadEvents:
    """ Downloads an HTML content of an events' pages parsed from websites' calendar pages.

    Stores event's URL, HTML file path and timestamp of a download into the database.
    Outputs a json file with the download info about most recent run of the script.
    """

    OUTPUT_FILE_PATH = "data/tmp/download_events_output.json"
    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.connection = utils.create_connection()
        self.base_dict = utils.load_base()

    def run(self) -> None:
        input_websites = self.load_input_websites()
        events_to_insert, log_info = self.download_events(input_websites)
        self.store_to_database(events_to_insert)
        utils.store_to_json_file(log_info, DownloadEvents.OUTPUT_FILE_PATH)

    def load_input_websites(self) -> list:
        with self.connection:
            cursor = self.connection.execute('''SELECT id, url FROM website WHERE is_parsed == 0''')
            return cursor.fetchall()

    def download_events(self, input_websites: list) -> (list, list):
        input_ids = [tuple[0] for tuple in input_websites]
        input_urls = [tuple[1] for tuple in input_websites]

        already_downloaded_events = self.load_already_downloaded_events()

        events_to_insert = []
        log_info = []

        for website in input_urls:
            website_events_to_insert, website_log_obj = self.process_website(website, already_downloaded_events)

            events_to_insert.extend(website_events_to_insert)
            log_info.append(website_log_obj)

        query = '''
            UPDATE website
            SET is_parsed = 1
            WHERE id IN ({})
        '''.format(",".join(['"{}"'.format(id) for id in input_ids]))

        with self.connection:
            self.connection.execute(query)

        return events_to_insert, log_info

    def load_already_downloaded_events(self):
        with self.connection:
            cursor = self.connection.execute('''SELECT url FROM event_raw''')
            return [url[0] for url in cursor.fetchall()]

    def process_website(self, url: str, already_downloaded_events: list) -> (list, dict):
        base = self.get_website_base(url)
        domain = base["domain"]

        events_to_insert = []
        website_log_obj = {
            "domain": domain,
            "files": []
        }

        xpaths = utils.get_xpaths(base["parser"])
        current_dir = os.path.join(DATA_DIR_PATH, domain)

        files = sorted([file for file in os.listdir(current_dir) if file.endswith('.html')], key=str.lower)
        for filename in files:
            file_log_obj = {
                "name": filename,
                "events_list": []
            }

            with open(os.path.join(current_dir, filename)) as html_file:
                dom = etree.parse(html_file, etree.HTMLParser())

            root = dom.xpath(xpaths["root"])[0]

            for el in root.xpath(xpaths["url"]):
                event_url = urllib.urljoin(url, el)

                if event_url not in already_downloaded_events:
                    html_file_dir = os.path.join(DATA_DIR_PATH, domain, DownloadEvents.EVENTS_FOLDER_NAME)
                    info_to_insert = utils.download_html_content(event_url, html_file_dir)

                    if info_to_insert:
                        events_to_insert.append(info_to_insert)
                        already_downloaded_events.append(event_url)

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
                url, html_file_path, downloaded_at = event_info

                sql_command = '''
                        INSERT INTO event_raw(url, html_file_path, downloaded_at)
                        VALUES(?, ?, ?)
                    '''
                values = (url, html_file_path, downloaded_at)

                self.connection.execute(sql_command, values)

            self.connection.commit()


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
