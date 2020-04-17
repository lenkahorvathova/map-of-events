import argparse
import json
import multiprocessing
import os
import sqlite3
import sys
from datetime import datetime

from lxml import etree

from lib import utils


class ParseEvents:
    """ Parses an HTML content of downloaded events for more information.

    Stores parsed events' information into the database.
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
    def process_event(input_tuple: tuple) -> (dict, str, int):
        input_index, total_length, event_tuple, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, event_tuple: (int, str, str, str), timestamp: datetime, 
            website_base: dict) """
        event_html_id, event_html_file_path, event_url, _ = event_tuple

        debug_output = "{}/{} | Parsing event: {}".format(input_index, total_length, event_url)

        if not event_html_file_path:
            debug_output += " | NOK - (file path is None!)"
            print(debug_output)
            return ()

        elif not os.path.isfile(event_html_file_path):
            debug_output += " | NOK - (file '{}' does not exist!)".format(event_html_file_path)
            print(debug_output)
            return ()

        with open(event_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser())

        xpaths = utils.get_xpaths(website_base["parser"])
        data_dict = {}
        for key, value_array in xpaths.items():
            if key == "root" or key == "url":
                continue
            for key_xpath in value_array:
                try:
                    xpath_value = dom.xpath(key_xpath)
                except Exception as e:
                    print(e)
                    xpath_value = None
                if xpath_value:
                    if key in data_dict:
                        data_dict[key].extend(xpath_value)
                    else:
                        data_dict[key] = xpath_value

        debug_output += " | OK".format(input_index, total_length, event_url)
        print(debug_output)

        return data_dict, timestamp, event_tuple

    def store_to_database(self, events_to_insert: list, dry_run: bool) -> None:
        debug_output = ">> Data to be stored in the DB:\n"
        nok = 0
        ok = 0

        for event_data in filter(None, events_to_insert):
            data_dict, parsed_at, event_tuple = event_data
            event_html_id, event_html_file_path, _, _ = event_tuple
            file_path_array = event_html_file_path.split('/')
            prepared_data = self.prepare_event_data(data_dict)

            if prepared_data["status"] == "error":
                debug_output += "{} | NOK - {} > {}\n".format("/".join(file_path_array[-3:]), prepared_data["message"],
                                                              data_dict)
                nok += 1
                continue

            debug_output += "{} | OK > {}\n".format("/".join(file_path_array[-3:]), json.dumps(prepared_data, indent=4))
            ok += 1

            if not dry_run:
                query = '''INSERT OR IGNORE INTO event_data(title, perex, organizer, types_data, location, gps_data, 
                                                            date_data)
                           VALUES(?, ?, ?, ?, ?, ?, ?)'''

                data = prepared_data["data"]
                values = (data["title"], data["perex"], data["organizer"], data["types_data"], data["location"],
                          data["gps_data"], data["date_data"])

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    nok += 1
                    ok -= 1
                    print("Error occurred when storing {} into 'event_data' table: {}".format(values, str(e)))

                self.connection.commit()

        debug_output += ">> Result: {} OKs + {} NOKs / {}\n".format(ok, nok, ok + nok)
        print(debug_output, end="")

    @staticmethod
    def prepare_event_data(data_dict: dict) -> dict:
        parsed_dict = {}

        # TITLE (required):
        if "title" in data_dict and data_dict["title"] is not None:
            parsed_dict["title"] = data_dict["title"][0]
        else:
            return {
                "status": "error",
                "message": "Title is missing!"
            }

        # PEREX:
        parsed_dict["perex"] = None
        if "perex" in data_dict:
            parsed_dict["perex"] = '\n'.join(ParseEvents.sanitize_array(data_dict["perex"]))

        # ORGANIZER:
        parsed_dict["organizer"] = None
        if "organizer" in data_dict and data_dict["organizer"][0] != '\n':
            parsed_dict["organizer"] = ', '.join(ParseEvents.sanitize_array(data_dict["organizer"]))

        # TYPES:
        parsed_dict["types_data"] = None
        if "types" in data_dict:
            types_array = []
            for type_group in data_dict["types"]:
                type_split = type_group.split(',')
                types_array.extend(type_split)
            parsed_dict["types_data"] = str(ParseEvents.sanitize_array(types_array))

        # LOCATION:
        parsed_dict["location"] = None
        if "location" in data_dict and data_dict["location"] is not None \
                and data_dict["location"][0] != "místo není uvedeno" \
                and data_dict["location"][0] != '\n':
            parsed_dict["location"] = ', '.join(ParseEvents.sanitize_array(data_dict["location"]))

        # GPS:
        parsed_dict["gps_data"] = None
        if "gps" in data_dict:
            parsed_dict["gps_data"] = str(ParseEvents.sanitize_array(data_dict["gps"]))

        # DATE (required):
        if "date" in data_dict and data_dict["date"] is not None \
                and data_dict["date"][0] != "akce není časově vymezena":
            if isinstance(data_dict["date"], list):
                parsed_dict["date_data"] = str(ParseEvents.sanitize_array(data_dict["date"]))
            else:
                parsed_dict["date_data"] = str([data_dict["date"].strip()])
        else:
            return {
                "status": "error",
                "message": "Date is missing!"
            }

        return {
            "status": "ok",
            "data": parsed_dict
        }

    @staticmethod
    def sanitize_array(array: list) -> list:
        array = [el.strip() for el in array]
        array = filter(None, array)

        return list(array)

    def update_database(self, input_events: list) -> None:
        input_ids = [event[0] for event in input_events]

        query = '''UPDATE event_html
                   SET is_parsed = 1
                   WHERE id IN ({})'''.format(",".join(['"{}"'.format(id) for id in input_ids]))

        self.connection.execute(query)
        self.connection.commit()


if __name__ == '__main__':
    parse_events = ParseEvents()
    parse_events.run()
