import argparse
import multiprocessing
import os
import sqlite3
import sys
import urllib.parse as urllib
from datetime import datetime

from lxml import etree

from lib import utils
from lib.parser import Parser


class ParseCalendars:
    """ Parses an HTML content of a website's calendar page for events' URLs.

    Stores parsed events' URLs into the database.
    """

    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_tables = utils.check_db_tables(self.connection, ["calendar", "event_url"])
            if len(missing_tables) != 0:
                raise Exception("Missing tables in the DB: {}".format(missing_tables))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="parse calendars only of the specified domain")
        parser.add_argument('--parse-all', action='store_true', default=False,
                            help="parse even already parsed calendars")

        return parser.parse_args()

    def run(self) -> None:
        input_calendars = self.load_input_calendars()
        events_to_insert = self.parse_calendars(input_calendars)

        if not self.args.dry_run:
            self.store_to_database(events_to_insert)
            self.update_database(input_calendars)
        self.connection.close()

    def load_input_calendars(self) -> list:
        print("Loading input calendars...")
        query = '''
                    SELECT id, url, html_file_path 
                    FROM calendar 
                    WHERE 1 == 1
                '''

        if self.args.domain:
            website_base = utils.get_base_by_domain(self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base.get('url', None)
            if calendar_url is None:
                sys.exit("Specified domain '{}' is no longer active!".format(self.args.domain))
            query += ''' AND url == "{}"'''.format(calendar_url)

        if not self.args.parse_all:
            query += ''' AND is_parsed == 0'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def parse_calendars(input_calendars: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, calendar_tuple in enumerate(input_calendars):
            _, calendar_url, _ = calendar_tuple
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_calendars), calendar_tuple, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            events_lists = p.map(ParseCalendars.process_calendar, input_tuples)

        events_to_insert = [event for sublist in events_lists for event in sublist]
        print(">> Number of ALL events: {}".format(len(events_to_insert)))

        return events_to_insert

    @staticmethod
    def process_calendar(input_tuple: tuple) -> list:
        input_index, total_length, calendar_tuple, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, calendar_tuple: (int, str, str), timestamp: datetime, 
            website_base: dict) """
        calendar_id, calendar_url, calendar_html_file_path = calendar_tuple

        domain = website_base["domain"]
        file = os.path.basename(calendar_html_file_path)

        debug_output = "{}/{} | {}/{}".format(input_index, total_length, domain, file)

        if not os.path.isfile(calendar_html_file_path):
            debug_output += " | File '{}' does not exist!".format(calendar_html_file_path)
            print(debug_output)
            return []

        with open(calendar_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser())

        parser_name = website_base["parser"]
        parser = Parser(parser_name)
        parser.set_dom(dom)
        event_urls = parser.get_event_urls()

        # if len(event_urls) == 0:
        #     debug_output += " | {}".format(" & ".join(parser.error_messages))
        #     print(debug_output)
        #     return []

        events_to_insert = []
        for index, url_path in enumerate(event_urls):
            event_url = urllib.urljoin(calendar_url, url_path)
            events_to_insert.append((event_url, timestamp, calendar_id))

        debug_output += " | {}\n".format(len(events_to_insert))
        # for event_url, _, _ in events_to_insert:
        #     debug_output += "\t Found URL: {}\n".format(event_url)
        print(debug_output, end="")

        return events_to_insert

    def store_to_database(self, events_to_insert: list) -> None:
        print("Inserting into DB...")

        count_query = '''
                          SELECT count(*) 
                          FROM event_url
                      '''
        cursor = self.connection.execute(count_query)
        events_count_before = int(cursor.fetchone()[0])

        for url, parsed_at, calendar_id in events_to_insert:
            query = '''
                        INSERT OR IGNORE INTO event_url(url, parsed_at, calendar_id)
                        VALUES(?, ?, ?)
                    '''
            values = (url, parsed_at, calendar_id)

            try:
                self.connection.execute(query, values)
            except sqlite3.Error as e:
                print("Error occurred when storing {} into 'event_url' table: {}".format(values, str(e)))
        self.connection.commit()

        cursor = self.connection.execute(count_query)
        events_count_after = int(cursor.fetchone()[0])

        events_count_new = events_count_after - events_count_before
        print(">> Number of NEW events: {}".format(events_count_new))

    def update_database(self, input_websites: list) -> None:
        print("Updating DB...")

        input_ids = [website[0] for website in input_websites]

        query = '''
                    UPDATE calendar
                    SET is_parsed = 1
                    WHERE id IN ({})
                '''.format(",".join(['"{}"'.format(calendar_id) for calendar_id in input_ids]))

        try:
            self.connection.execute(query)
        except sqlite3.Error as e:
            print("Error occurred when updating 'is_parsed' value in 'calendar' table: {}".format(str(e)))
        self.connection.commit()


if __name__ == '__main__':
    parse_calendars = ParseCalendars()
    parse_calendars.run()
