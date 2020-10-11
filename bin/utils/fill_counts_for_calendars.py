import argparse
import json
import multiprocessing
import os
import sqlite3
import urllib.parse as urllib
from datetime import datetime

from lxml import etree

from lib import utils
from lib.parser import Parser


class FillCountsForCalendars:

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

        return parser.parse_args()

    def run(self) -> None:
        input_calendars = self.load_input_calendars()
        events_to_insert = self.parse_calendars(input_calendars)
        events_counts = self.get_new_counts(events_to_insert)

        if self.args.dry_run:
            print(json.dumps(events_to_insert, indent=4))
        else:
            self.update_database(events_counts)
        self.connection.close()

    def load_input_calendars(self) -> list:
        print("Loading input calendars...")
        query = '''
                    SELECT id, url, html_file_path 
                    FROM calendar 
                '''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def parse_calendars(input_calendars: list) -> dict:
        timestamp = datetime.now()
        input_tuples = []

        for index, calendar_tuple in enumerate(input_calendars):
            _, calendar_url, _ = calendar_tuple
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_calendars), calendar_tuple, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            events_lists = p.map(FillCountsForCalendars.process_calendar, input_tuples)

        events_to_insert = {calendar_id: {'all': len(events_list), 'new': 0}
                            for element in events_lists
                            for calendar_id, events_list in element.items()}
        return events_to_insert

    @staticmethod
    def process_calendar(input_tuple: tuple) -> dict:
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

        debug_output += " | {}\n".format(len(events_to_insert))
        print(debug_output, end="")

        return {
            calendar_id: events_to_insert
        }

    def get_new_counts(self, events_to_insert: dict) -> dict:
        query = '''
                    SELECT 
                        c.id AS calendar_id,
                        count(eu.url) AS events_count
                    FROM calendar c
                        LEFT OUTER JOIN event_url eu ON c.id = eu.calendar_id
                    WHERE eu.url IS NOT NULL
                    GROUP BY calendar_id
                '''
        cursor = self.connection.execute(query)

        for calendar_id, events_count in cursor.fetchall():
            if calendar_id in events_to_insert:
                events_to_insert[calendar_id]['new'] = int(events_count)

        return events_to_insert

    def update_database(self, events_counts: dict) -> None:
        print("Updating DB...")

        for calendar_id, counts in events_counts.items():
            query = '''
                        UPDATE calendar
                        SET all_event_url_count = {}, 
                            new_event_url_count = {}
                        WHERE id = {}
                    '''.format(counts['all'], counts['new'], calendar_id)
            try:
                self.connection.execute(query)
            except sqlite3.Error as e:
                print("Error occurred when updating 'is_parsed' value in 'calendar' table: {}".format(str(e)))
        self.connection.commit()


if __name__ == '__main__':
    fill_counts_for_calendars = FillCountsForCalendars()
    fill_counts_for_calendars.run()
