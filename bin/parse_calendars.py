import argparse
import logging
import multiprocessing
import os
import sqlite3
import sys
import urllib.parse as urllib
from datetime import datetime

from lxml import etree

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import SIMPLE_LOGGER_PREFIX
from lib.parser import Parser


class ParseCalendars:
    """ Parses an HTML content of a website's calendar page for events' URLs.

    Stores parsed events' URLs into the database.
    """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_tables = utils.check_db_tables(self.connection, ["calendar", "event_url"])
            if len(missing_tables) != 0:
                exception_msg = "Missing tables in the DB: {}".format(missing_tables)
                self.logger.critical(exception_msg)
                raise Exception(exception_msg)

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()

        parser.add_argument('--domain', type=str, default=None,
                            help="parse calendars only of the specified domain")
        parser.add_argument('--parse-all', action='store_true', default=False,
                            help="parse even already parsed calendars")

        return parser.parse_args()

    def run(self) -> None:
        input_calendars = self.load_input_calendars()
        events_to_insert = self.parse_calendars(input_calendars)

        if not self.args.dry_run:
            events_counts = self.store_to_database(events_to_insert)
            self.update_database(events_counts)
        self.connection.close()

    def load_input_calendars(self) -> list:
        self.logger.info("Loading input calendars...")
        query = '''
                    SELECT id, url, html_file_path 
                    FROM calendar 
                    WHERE 1 == 1
                '''

        if self.args.domain:
            website_base = utils.get_base_by_domain(self.args.domain)
            if website_base is None:
                self.logger.critical("Unknown domain '{}'!".format(self.args.domain))
                sys.exit()
            calendar_url = website_base.get('url', None)
            if calendar_url is None:
                self.logger.critical("Specified domain '{}' is no longer active!".format(self.args.domain))
                sys.exit()
            query += ''' AND url == "{}"'''.format(calendar_url)

        if not self.args.parse_all:
            query += ''' AND is_parsed == 0'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def parse_calendars(self, input_calendars: list) -> dict:
        self.logger.info("Parsing calendars' content...")
        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__)
        timestamp = datetime.now()
        input_tuples = []

        for index, calendar_tuple in enumerate(input_calendars):
            _, calendar_url, _ = calendar_tuple
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_calendars), calendar_tuple, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            events_lists = p.map(ParseCalendars.process_calendar, input_tuples)

        events_to_insert = {calendar_id: events_list
                            for element in events_lists
                            for calendar_id, events_list in element.items()}
        return events_to_insert

    @staticmethod
    def process_calendar(input_tuple: tuple) -> dict:
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)
        input_index, total_length, calendar_tuple, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, calendar_tuple: (int, str, str), timestamp: datetime, 
            website_base: dict) """
        calendar_id, calendar_url, calendar_html_file_path = calendar_tuple

        domain = website_base["domain"]
        file = os.path.basename(calendar_html_file_path)

        info_output = "{}/{} | {}/{}".format(input_index, total_length, domain, file)

        if not os.path.isfile(calendar_html_file_path):
            info_output += " | File '{}' does not exist!".format(calendar_html_file_path)
            simple_logger.warning(info_output)
            return {
                calendar_id: []
            }

        with open(calendar_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser())

        parser_name = website_base["parser"]
        parser = Parser(parser_name)
        parser.set_dom(dom)
        event_urls = parser.get_event_urls()

        events_to_insert = []
        for index, url_path in enumerate(event_urls):
            event_url = urllib.urljoin(calendar_url, url_path)
            events_to_insert.append((event_url, timestamp))

        info_output += " | {}".format(len(events_to_insert))
        simple_logger.info(info_output)

        if len(events_to_insert) == 0:
            simple_logger.debug("\t Parser's errors: {}".format(" & ".join(parser.error_messages)))
        for event_url, _ in events_to_insert:
            simple_logger.debug("\t Found URL: {}".format(event_url))

        return {
            calendar_id: events_to_insert
        }

    def store_to_database(self, events_to_insert: dict) -> dict:
        self.logger.info("Inserting into DB...")
        events_counts_dict = {}
        count_query = '''
                          SELECT count(*) 
                          FROM event_url
                      '''

        events_count_all_found = 0
        events_count_new_found = 0
        for calendar_id, events_list in events_to_insert.items():
            if len(events_list) == 0:
                events_counts_dict[calendar_id] = {
                    'all': 0,
                    'new': 0
                }
                continue

            cursor = self.connection.execute(count_query)
            events_count_before = int(cursor.fetchone()[0])

            for url, parsed_at in events_list:
                query = '''
                            INSERT OR IGNORE INTO event_url(url, parsed_at, calendar_id)
                            VALUES(?, ?, ?)
                        '''
                values = (url, parsed_at, calendar_id)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    self.logger.error(
                        "Error occurred when storing {} into 'event_url' table: {}".format(values, str(e)))

            cursor = self.connection.execute(count_query)
            events_count_after = int(cursor.fetchone()[0])

            events_counts_dict[calendar_id] = {
                'all': len(events_list),
                'new': events_count_after - events_count_before
            }
            events_count_all_found += events_counts_dict[calendar_id]['all']
            events_count_new_found += events_counts_dict[calendar_id]['new']

        self.connection.commit()

        self.logger.info(">> Number of ALL events found: {}".format(events_count_all_found))
        self.logger.info(">> Number of NEW events found: {}".format(events_count_new_found))

        return events_counts_dict

    def update_database(self, events_counts: dict) -> None:
        self.logger.info("Updating DB...")

        for calendar_id, counts in events_counts.items():
            query = '''
                        UPDATE calendar
                        SET is_parsed = 1, 
                            all_event_url_count = {}, 
                            new_event_url_count = {}
                        WHERE id = {}
                    '''.format(counts['all'], counts['new'], calendar_id)
            try:
                self.connection.execute(query)
            except sqlite3.Error as e:
                self.logger.error(
                    "Error occurred when updating 'is_parsed' value in 'calendar' table: {}".format(str(e)))
        self.connection.commit()


if __name__ == '__main__':
    parse_calendars = ParseCalendars()
    parse_calendars.run()
