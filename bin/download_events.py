import argparse
import os
import urllib.parse as urllib
from datetime import datetime

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
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()
        self.base_dict = utils.load_base()

    @staticmethod
    def _parse_arguments():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="download events only for the specified domain")  # TODO

        return parser.parse_args()

    def run(self) -> None:
        input_ids, input_urls = self.load_input_websites()
        events_to_insert, log_info = self.download_events(input_urls)
        utils.store_to_json_file(log_info, DownloadEvents.OUTPUT_FILE_PATH)

        if not self.args.dry_run:
            self.store_to_database(events_to_insert)
            self.update_database(input_ids)

    def load_input_websites(self) -> (list, list):
        with self.connection:
            cursor = self.connection.execute('''SELECT id, url FROM website WHERE is_parsed == 0''')
            websites_tuples = cursor.fetchall()

        return [tuple[0] for tuple in websites_tuples], [tuple[1] for tuple in websites_tuples]

    def download_events(self, input_urls: list) -> (list, dict):
        timestamp = datetime.now()

        events_to_insert = []
        log_info = {
            "events_count": 0,
            "websites_count": len(input_urls),
            "websites_info": []
        }

        index = 1
        for website in input_urls:
            # Note: if input websites get bigger, formatting for leading zeros need to be changed accordingly
            print("{:03d}/{} | ".format(index, len(input_urls)), end="")
            index += 1

            already_downloaded_events = self.load_website_events(website)
            website_events_to_insert, website_log_obj = self.process_website(website, timestamp,
                                                                             already_downloaded_events)
            events_to_insert.extend(website_events_to_insert)
            log_info["events_count"] += website_log_obj["events_count"]
            log_info["websites_info"].append(website_log_obj)

        return events_to_insert, log_info

    def load_website_events(self, url: str):
        with self.connection:
            query = '''SELECT url FROM event_raw WHERE url LIKE "{}%"'''.format(url[:-3])  # TODO
            cursor = self.connection.execute(query)
            return [url[0] for url in cursor.fetchall()]

    def process_website(self, url: str, timestamp: datetime, already_downloaded_events: list) -> (list, dict):
        base = self.get_website_base_by("url", url)
        domain = base["domain"]
        print("{}".format(domain))

        events_to_insert = []
        website_log_obj = {
            "domain": domain,
            "events_count": 0,
            "files": []
        }

        xpaths = utils.get_xpaths(base["parser"])
        current_dir = os.path.join(DATA_DIR_PATH, domain)

        files = sorted([file for file in os.listdir(current_dir) if file.endswith('.html')], key=str.lower)
        for calendar_file_name in files:
            file_log_obj = {
                "name": calendar_file_name,
                "events_count": 0,
                "events_list": []
            }

            with open(os.path.join(current_dir, calendar_file_name)) as html_file:
                dom = etree.parse(html_file, etree.HTMLParser())

            root = dom.xpath(xpaths["root"])[0]
            index = 1

            for el in root.xpath(xpaths["url"]):
                event_url = urllib.urljoin(url, el)

                if event_url not in already_downloaded_events:
                    event_file_dir = os.path.join(DATA_DIR_PATH, domain, DownloadEvents.EVENTS_FOLDER_NAME)
                    event_file_name = calendar_file_name + "_" + str(index)
                    html_file_path = os.path.join(event_file_dir, event_file_name + ".html")

                    try:
                        os.makedirs(event_file_dir, exist_ok=True)

                        print("\t", end="")

                        if not self.args.dry_run:
                            utils.download_html_content(event_url, html_file_path)
                        else:
                            print("Would download URL ", event_url)

                        events_to_insert.append((event_url, html_file_path, timestamp))
                        already_downloaded_events.append(event_url)
                        file_log_obj["events_list"].append(event_url)

                        index += 1

                    except Exception:
                        print("Something went wrong when downloading {}.".format(event_url))

            file_log_obj["events_count"] = len(file_log_obj["events_list"])
            website_log_obj["events_count"] += len(file_log_obj["events_list"])
            website_log_obj["files"].append(file_log_obj)

        return events_to_insert, website_log_obj

    def get_website_base_by(self, attr: str, value: str) -> dict:
        for obj in self.base_dict:
            if obj[attr] == value:
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

                import sqlite3
                try:
                    self.connection.execute(sql_command, values)
                except sqlite3.IntegrityError:
                    print(values)

            self.connection.commit()

    def update_database(self, input_ids: list) -> None:
        query = '''
            UPDATE website
            SET is_parsed = 1
            WHERE id IN ({})
        '''.format(",".join(['"{}"'.format(id) for id in input_ids]))

        with self.connection:
            self.connection.execute(query)


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
