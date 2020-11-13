import argparse
import logging
import multiprocessing
import os
import sqlite3
import sys
from datetime import datetime

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import DATA_DIR_PATH, INPUT_SITES_BASE_FILE_PATH, SIMPLE_LOGGER_PREFIX


class DownloadCalendars:
    """ Downloads an HTML content of a website's calendar page of input websites specified in the base file.

    Stores calendar's information into the database.
    """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            if not os.path.isfile(INPUT_SITES_BASE_FILE_PATH):
                exception_msg = "Missing an input base file: '{}'".format(INPUT_SITES_BASE_FILE_PATH)
                self.logger.critical(exception_msg)
                raise Exception(exception_msg)
            missing_tables = utils.check_db_tables(self.connection, ["calendar"])
            if len(missing_tables) != 0:
                exception_msg = ("Missing tables in the DB: {}".format(missing_tables))
                self.logger.critical(exception_msg)
                raise Exception(exception_msg)

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()

        parser.add_argument('--domain', type=str, default=None,
                            help="download events only for the specified domain")

        return parser.parse_args()

    def run(self) -> None:
        input_websites = self.get_input_websites()
        calendars_to_insert = self.download_calendars(input_websites)
        self.store_to_database(calendars_to_insert, self.args.dry_run)
        self.connection.close()

    def get_input_websites(self) -> list:
        self.logger.info("Loading input calendars...")

        if self.args.domain:
            website_base = utils.get_base_by_domain(self.args.domain)
            if website_base is None:
                self.logger.critical("Unknown domain '{}'!".format(self.args.domain))
                sys.exit()
            calendar_url = website_base.get('url', None)
            if calendar_url is None:
                self.logger.critical("Specified domain '{}' is no longer active!".format(self.args.domain))
                sys.exit()

            return [website_base]

        base_list = utils.get_active_base()
        return base_list

    def download_calendars(self, base_list: list) -> list:
        self.logger.info("Downloading calendars' content...")
        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__)
        timestamp = datetime.now()
        input_tuples = []

        for index, website_base in enumerate(base_list):
            input_tuples.append((index + 1, len(base_list), timestamp, website_base, self.args.dry_run))

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadCalendars.process_website, input_tuples)

    @staticmethod
    def process_website(input_tuple: tuple) -> (str, str, str):
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)
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

        info_output = "{}/{}".format(input_index, total_length)
        info_output += " | Downloading URL: {} | {}".format(str(url), str(result))
        simple_logger.info(info_output)

        return url, html_file_path, timestamp

    def store_to_database(self, calendars_to_insert: list, dry_run: str) -> None:
        if not dry_run:
            self.logger.info("Inserting into DB...")

        failed_calendars = []

        for calendar_info in calendars_to_insert:
            url, html_file_path, downloaded_at = calendar_info

            if html_file_path is None:
                failed_calendars.append(url)
                continue

            if not dry_run:
                query = '''
                            INSERT INTO calendar(url, html_file_path, downloaded_at)
                            VALUES (?, ?, ?)
                        '''
                values = (url, html_file_path, downloaded_at)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    self.logger.error("Error occurred when storing {} into 'calendar' table: {}".format(values, str(e)))

        if not dry_run:
            self.connection.commit()

        self.logger.info(">> Number of failed calendars: {}/{}".format(len(failed_calendars), len(calendars_to_insert)))
        self.logger.info(">> Failed calendars: {}".format(failed_calendars))


if __name__ == '__main__':
    download_calendars = DownloadCalendars()
    download_calendars.run()
