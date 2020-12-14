import argparse
import logging
import multiprocessing
import os
import sqlite3
import sys
from datetime import datetime
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import DATA_DIR_PATH, INPUT_SITES_BASE_FILE_PATH, SIMPLE_LOGGER_PREFIX


class DownloadCalendars:
    """ Downloads a calendar page HTML content of input websites specified in the base file. """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, log_level=self.args.log_level)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_file(INPUT_SITES_BASE_FILE_PATH)
            utils.check_db_tables(self.connection, ["calendar"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Downloads a calendar page HTML content of input websites specified in the base file.")
        parser.add_argument('--domain', type=str, default=None,
                            help="download content only of the specified calendar domain")
        return parser.parse_args()

    def run(self) -> None:
        input_calendars = self._load_input_calendars()
        calendars_to_insert = self._download_calendars(input_calendars)
        self._store_to_database(calendars_to_insert)
        self.connection.close()

    def _load_input_calendars(self) -> List[dict]:
        self.logger.info("Loading input calendars...")

        if self.args.domain:
            website_base = utils.get_base_by_domain(self.args.domain)
            if website_base is None:
                self.logger.critical("Unknown domain '{}'!".format(self.args.domain))
                sys.exit()
            if website_base.get('url', None) is None:
                self.logger.critical("Specified domain '{}' is no longer active!".format(self.args.domain))
                sys.exit()
            return [website_base]

        base_list = utils.get_active_base()
        return base_list

    def _download_calendars(self, input_calendars: List[dict]) -> List[tuple]:
        self.logger.info("Downloading calendars...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__,
                                    log_file=self.args.log_file, log_level=self.args.log_level)
        timestamp = datetime.now()
        input_tuples = []
        for index, website_base in enumerate(input_calendars):
            input_tuples.append((index + 1, len(input_calendars), timestamp, website_base, self.args.dry_run))

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadCalendars._download_calendars_process, input_tuples)

    @staticmethod
    def _download_calendars_process(input_tuple: (int, int, datetime, dict, bool)) -> (str, str, datetime):
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, timestamp, website_base, dry_run = input_tuple
        url = website_base["url"]

        html_file_dir = os.path.join(DATA_DIR_PATH, website_base["domain"])
        html_file_path = os.path.join(html_file_dir, timestamp.strftime("%Y-%m-%d_%H-%M-%S") + ".html")

        os.makedirs(html_file_dir, exist_ok=True)
        result = utils.download_html_content(url, html_file_path,
                                             verify=website_base.get("verify", True), dry_run=dry_run)
        if result != "200":
            html_file_path = None

        simple_logger.info("{}/{} | Downloading URL: {} | {}".format(input_index, total_length, str(url), str(result)))

        return url, html_file_path, timestamp

    def _store_to_database(self, calendars_to_insert: List[tuple]) -> None:
        if not self.args.dry_run:
            self.logger.info("Inserting into DB...")

        failed_calendars = []
        for calendar_info in calendars_to_insert:
            url, html_file_path, downloaded_at = calendar_info

            if html_file_path is None:
                failed_calendars.append(url)
                continue

            if not self.args.dry_run:
                query = '''
                            INSERT INTO calendar(url, html_file_path, downloaded_at)
                            VALUES (?, ?, ?)
                        '''
                values = (url, html_file_path, downloaded_at)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    self.logger.error("Error occurred when storing {} into 'calendar' table: {}".format(values, str(e)))

        if not self.args.dry_run:
            self.connection.commit()

        self.logger.info(">> Number of failed calendars: {}/{}".format(len(failed_calendars), len(calendars_to_insert)))
        self.logger.info(">> Failed calendar URLs: {}".format(failed_calendars))


if __name__ == '__main__':
    download_calendars = DownloadCalendars()
    download_calendars.run()
