import argparse
import json
import multiprocessing
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

from lxml import etree

from lib import utils
from lib.parser import Parser


class ParseEvents:
    """ Parses an HTML content of downloaded events for more information.

    Stores parsed events' information into the database.
    """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()
        self.base = utils.load_base()

        if not self.args.dry_run:
            missing_tables = utils.check_db(self.connection, ["calendar", "event_url", "event_html", "event_data"])
            if len(missing_tables) != 0:
                raise Exception("Missing tables in the DB: {}".format(missing_tables))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="parse events only of the specified domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="parse events' data of the specified URL")
        parser.add_argument('--parse-all', action='store_true', default=False,
                            help="parse even already parsed events")

        return parser.parse_args()

    def run(self) -> None:
        input_events = self.load_input_events()
        events_to_insert = self.parse_events(input_events)
        self.store_to_database(events_to_insert, self.args.dry_run)
        if not self.args.dry_run:
            self.update_database(input_events)
        self.connection.close()

    def load_input_events(self) -> list:
        print("Loading input events...")
        query = '''SELECT eh.id, eh.html_file_path, eu.url, c.url FROM event_html eh 
                   INNER JOIN event_url eu ON eh.event_url_id = eu.id 
                   INNER JOIN calendar c ON eu.calendar_id = c.id WHERE 1==1'''

        if self.args.domain:
            website_base = utils.get_base_by("domain", self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base["url"]
            query += ''' AND c.url = "{}"'''.format(calendar_url)

        if self.args.event_url:
            query += ''' AND eu.url = "{}"'''.format(self.args.event_url)

        if not self.args.parse_all:
            query += ''' AND eh.is_parsed == 0'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def parse_events(input_events: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, event_tuple in enumerate(input_events):
            _, _, _, calendar_url = event_tuple
            website_base = utils.get_base_by("url", calendar_url)
            input_tuples.append((index + 1, len(input_events), event_tuple, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            return p.map(ParseEvents.process_event, input_tuples)

    @staticmethod
    def process_event(input_tuple: tuple) -> (dict, str, tuple):
        input_index, total_length, event_tuple, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, event_tuple: (int, str, str, str), timestamp: datetime, 
            website_base: dict) """
        event_html_id, event_html_file_path, event_url, _ = event_tuple

        debug_output = "{}/{} | Parsing event: {}".format(input_index, total_length, event_url)

        if not event_html_file_path:
            debug_output += " | NOK - (File path for the event '{}' is None!)".format(event_url)
            print(debug_output)
            return {"error": "Filepath is None!"}, timestamp, event_tuple

        elif not os.path.isfile(event_html_file_path):
            debug_output += " | NOK - (File '{}' does not exist!)".format(event_html_file_path)
            print(debug_output)
            return {"error": "File does not exist!"}, timestamp, event_tuple

        with open(event_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser(encoding="utf-8"))

        parser_name = website_base["parser"]
        parser = Parser(parser_name)
        parser.set_dom(dom)

        try:
            parsed_event_data = parser.get_event_data()
        except Exception as e:
            debug_output += " | NOK"
            if len(parser.error_messages) != 0:
                debug_output += " - ({})".format(" & ".join(parser.error_messages))
            debug_output += "\n\t> Exception: {}".format(str(e))
            print(debug_output)
            return {"error": "Exception occurred during parsing!"}, timestamp, event_tuple

        if len(parsed_event_data) == 0:
            debug_output += " | NOK - ({})".format(" & ".join(parser.error_messages))
            print(debug_output)
            return {"error": "No data were parsed!"}, timestamp, event_tuple

        debug_output += " | OK".format(input_index, total_length, event_url)
        if len(parser.error_messages) != 0:
            debug_output += " - ({})".format(" & ".join(parser.error_messages))
        print(debug_output)

        return parsed_event_data, timestamp, event_tuple

    def store_to_database(self, events_to_insert: list, dry_run: bool) -> None:
        if not dry_run:
            print("Inserting into DB...")

        debug_output = ""
        parsed_data = []
        error_dict = defaultdict(int)
        nok_list = []
        ok = 0

        for event_data in events_to_insert:
            data_dict, parsed_at, event_tuple = event_data
            event_html_id, event_html_file_path, event_url, _ = event_tuple

            if "error" in data_dict:
                nok_list.append(event_html_id)
                error_dict[data_dict["error"]] += 1
                parsed_data.append({
                    "file": event_html_file_path if event_html_file_path else None,
                    "url": event_url if event_url else None,
                    "error": data_dict["error"]
                })
                continue

            title = data_dict.get("title", None)
            datetime = data_dict.get("datetime", None)

            if not title or not datetime:
                nok_list.append(event_html_id)
                error_dict["Doesn't contain title or datetime!"] += 1
                parsed_data.append({
                    "file": event_html_file_path,
                    "url": event_url,
                    "error": "Doesn't contain title or datetime!",
                    "data": data_dict
                })
                continue

            if not dry_run:
                query = '''INSERT INTO event_data(title, perex, datetime, location, gps, organizer, types, event_html_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                values = (data_dict.get("title"), data_dict.get("perex", None), data_dict.get("datetime"),
                          data_dict.get("location", None), data_dict.get("gps", None), data_dict.get("organizer", None),
                          data_dict.get("types", None), event_html_id)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    nok_list.append(event_html_id)
                    error_dict["Error occurred during storing!"] += 1
                    print("Error occurred when storing {} into 'event_data' table: {}".format(values, str(e)))
                    parsed_data.append({
                        "file": event_html_file_path,
                        "url": event_url,
                        "error": "Error occurred during storing!",
                        "data": data_dict
                    })
                    continue
            ok += 1
            parsed_data.append({
                "file": event_html_file_path,
                "url": event_url,
                "data": data_dict
            })
        self.connection.commit()

        if dry_run:
            debug_output += ">> Data:\n"
            debug_output += "{}\n".format(json.dumps(parsed_data, indent=4, ensure_ascii=False))

        debug_output += ">> Errors stats: {}\n".format(json.dumps(error_dict, indent=4, ensure_ascii=False))
        debug_output += ">> Result: {} OKs + {} NOKs / {}\n".format(ok, len(nok_list), ok + len(nok_list))
        debug_output += ">> Failed event_html IDs: {}\n".format(nok_list)
        print(debug_output, end="")

    def update_database(self, input_events: list) -> None:
        print("Updating DB...")

        input_ids = [event[0] for event in input_events]
        query = '''UPDATE event_html
                   SET is_parsed = 1
                   WHERE id IN ({})'''.format(",".join(['"{}"'.format(calendar_id) for calendar_id in input_ids]))

        try:
            self.connection.execute(query)
        except sqlite3.Error as e:
            print("Error occurred when updating 'is_parsed' in 'event_html' table: {}".format(str(e)))
        self.connection.commit()


if __name__ == '__main__':
    parse_events = ParseEvents()
    parse_events.run()
