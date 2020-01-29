import argparse
import multiprocessing
import os
import sqlite3
import urllib.parse as urllib
from datetime import datetime

from lxml import etree

from lib import utils


class ParseCalendars:
    """ Parses an HTML content of a website's calendar page for events' URLs.

    Stores parsed events' URLs into the database.
    """

    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

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
        calendar_url = None
        if self.args.domain:
            base = utils.get_base_by("domain", self.args.domain)
            calendar_url = base["url"]

        input_calendars = self.load_input_calendars(calendar_url)
        events_to_insert = self.parse_calendars(input_calendars)

        if not self.args.dry_run:
            self.store_to_database(events_to_insert)
            self.update_database(input_calendars)

        self.connection.close()

    def load_input_calendars(self, calendar_url: str = None) -> list:
        query = '''SELECT id, url, html_file_path FROM calendar WHERE 1==1'''

        if calendar_url:
            query += ''' AND url == "{}"'''.format(calendar_url)
        if not self.args.parse_all:
            query += ''' AND is_parsed == 0'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def parse_calendars(input_calendars: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, calendar in enumerate(input_calendars):
            _, calendar_url, _ = calendar
            website_base = utils.get_base_by("url", calendar_url)
            input_tuples.append((index + 1, len(input_calendars), calendar, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            events_lists = p.map(ParseCalendars.process_calendar, input_tuples)

        events_to_insert = [event for sublist in events_lists for event in sublist]
        print("Number of ALL events found: {}".format(len(events_to_insert)))

        return events_to_insert

    @staticmethod
    def process_calendar(input_tuple: tuple) -> list:
        input_index, total_length, calendar, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, calendar: (int, str, str), timestamp: datetime, 
            website_base: dict) """
        calendar_id, calendar_url, calendar_html_file_path = calendar

        domain = website_base["domain"]
        xpaths = utils.get_xpaths(website_base["parser"])

        if not os.path.isfile(calendar_html_file_path):
            print("{}/{} | {} | file '{}' does not exist!".format(input_index, total_length, domain,
                                                                  calendar_html_file_path))
            return []

        events_to_insert = []

        with open(calendar_html_file_path) as html_file:
            dom = etree.parse(html_file, etree.HTMLParser())

        root_list = dom.xpath(xpaths["root"])
        if len(root_list) == 0:
            print("{}/{} | {} | element '{}' doesn't exist!".format(input_index, total_length, domain,
                                                                    xpaths["root"]))
            return []

        root = root_list[0]
        url_elements = root.xpath(xpaths["url"])

        for index, el in enumerate(url_elements):
            event_url = urllib.urljoin(calendar_url, el)
            events_to_insert.append((event_url, timestamp, calendar_id))

        debug_output = "{}/{} | {} | {} events\n".format(input_index, total_length, domain, len(events_to_insert))
        # for event_url, _, _ in events_to_insert:
        #   debug_output += "\t Found URL: {}\n".format(event_url)
        print(debug_output, end="")

        return events_to_insert

    def store_to_database(self, events_to_insert: list) -> None:
        cursor = self.connection.execute('''SELECT COUNT(*) FROM event_url''')
        events_count_before = int(cursor.fetchone()[0])

        for event_info in events_to_insert:
            url, parsed_at, calendar_id = event_info

            query = '''INSERT OR IGNORE INTO event_url(url, parsed_at, calendar_id)
                       VALUES(?, ?, ?)'''
            values = (url, parsed_at, calendar_id)

            try:
                self.connection.execute(query, values)
            except sqlite3.Error as e:
                print("Error occurred when storing {} into 'event_url' table: {}".format(values, str(e)))

        self.connection.commit()

        cursor = self.connection.execute('''SELECT COUNT(*) FROM event_url''')
        events_count_after = int(cursor.fetchone()[0])

        events_count_new = events_count_after - events_count_before
        print("Number of NEW events found: {}".format(events_count_new))

    def update_database(self, input_websites: list) -> None:
        input_ids = [website[0] for website in input_websites]

        query = '''UPDATE calendar
                   SET is_parsed = 1
                   WHERE id IN ({})'''.format(",".join(['"{}"'.format(id) for id in input_ids]))

        self.connection.execute(query)
        self.connection.commit()


if __name__ == '__main__':
    parse_calendars = ParseCalendars()
    parse_calendars.run()
