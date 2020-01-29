import argparse
import multiprocessing
import os
import sys
from datetime import datetime

from lib import utils
from lib.constants import DATA_DIR_PATH


class DownloadCalendars:
    """ Downloads an HTML content of a calendar page of input websites specified in the base file.

    Stores calendar's information into the database.
    """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()
        self.base = utils.load_base()

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="download events only for the specified domain")

        return parser.parse_args()

    def run(self) -> None:
        base_list = self.base
        if self.args.domain:
            website_base = utils.get_base_by("domain", self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            base_list = [website_base]

        calendars_to_insert = self.download_calendars(base_list)
        if not self.args.dry_run:
            self.store_to_database(calendars_to_insert)

        self.connection.close()

    def download_calendars(self, base_list: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, website_base in enumerate(base_list):
            input_tuples.append((index + 1, len(base_list), timestamp, website_base, self.args.dry_run))

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadCalendars.process_website, input_tuples)

    @staticmethod
    def process_website(input_tuple: tuple) -> (str, str, str):
        input_index, total_length, timestamp, website_base, dry_run = input_tuple
        """ (input_index: int, total_length: int, timestamp: datetime, website_base: dict, dry_run: bool) """

        domain = website_base["domain"]
        url = website_base["url"]

        html_file_dir = os.path.join(DATA_DIR_PATH, domain)
        html_file_name = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        html_file_path = os.path.join(html_file_dir, html_file_name + ".html")

        os.makedirs(html_file_dir, exist_ok=True)
        result = utils.download_html_content(url, html_file_path, dry_run)
        if result != "200":
            html_file_path = None

        debug_output = "{}/{} | ".format(input_index, total_length)
        debug_output += "Downloading URL: " + str(url) + " (" + str(result) + ")"
        print(debug_output)

        return url, html_file_path, timestamp

    def store_to_database(self, calendars_to_insert: list) -> None:
        failed_calendars = []

        for calendar_info in calendars_to_insert:
            url, html_file_path, downloaded_at = calendar_info

            if html_file_path is None:
                domain = utils.get_domain_name(url)
                failed_calendars.append(domain)
                continue

            sql_command = '''INSERT INTO calendar(url, html_file_path, downloaded_at)
                             VALUES (?, ?, ?)'''
            values = (url, html_file_path, downloaded_at)

            self.connection.execute(sql_command, values)

        self.connection.commit()

        print("Number of failed calendars: {}/{}".format(len(failed_calendars), len(calendars_to_insert)))
        print("Failed calendars: {}".format(failed_calendars))


if __name__ == '__main__':
    download_calendars = DownloadCalendars()
    download_calendars.run()
