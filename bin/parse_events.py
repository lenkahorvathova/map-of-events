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
        self.get_statistics(input_events, events_to_insert)

        self.store_to_database(events_to_insert, self.args.dry_run)
        if not self.args.dry_run:
            self.update_database(input_events)

        self.connection.close()

    def load_input_events(self) -> list:
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
            events_lists = p.map(ParseEvents.process_event, input_tuples)

        return events_lists

    @staticmethod
    def process_event(input_tuple: tuple) -> (dict, str, int):
        input_index, total_length, event_tuple, timestamp, website_base = input_tuple
        """ (input_index: int, total_length: int, event_tuple: (int, str, str, str), timestamp: datetime, 
            website_base: dict) """
        event_html_id, event_html_file_path, event_url, calendar_url = event_tuple

        xpaths = utils.get_xpaths(website_base["parser"])
        debug_output = "{}/{} | Parsing event: {}".format(input_index, total_length, event_url)

        if not event_html_file_path:
            debug_output += " | NOK - (file path is None!)"
            print(debug_output)
            return ()

        if event_html_file_path and not os.path.isfile(event_html_file_path):
            debug_output += " | NOK - (file '{}' does not exist!)".format(event_html_file_path)
            print(debug_output)
            return ()

        with open(event_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser())

        data_dict = {}
        for key, value in xpaths.items():
            xpath_value = dom.xpath(value)
            if xpath_value:
                data_dict[key] = xpath_value

        debug_output += " | OK".format(input_index, total_length, event_url)
        print(debug_output)

        return data_dict, timestamp, event_html_id

    @staticmethod
    def get_statistics(input_events: list, events_to_insert: list) -> None:
        all_good = 0
        error = 0
        sth_bad = 0
        missing_title, missing_title_list = 0, []
        missing_perex = 0
        missing_date, missing_date_list = 0, []
        missing_location, missing_location_list = 0, []
        missing_gps = 0
        missing_organizer = 0
        missing_type = 0

        for event in events_to_insert:
            if not event:
                error += 1
                continue

            data_dict, _, event_html_id = event
            missing_property = False

            if "title" not in data_dict:
                missing_title += 1
                missing_title_list.append(str(event_html_id))
                missing_property = True
            if "perex" not in data_dict:
                missing_perex += 1
                missing_property = True
            if "date" not in data_dict:
                missing_date += 1
                missing_date_list.append(str(event_html_id))
                missing_property = True
            if "location" not in data_dict:
                missing_location += 1
                missing_location_list.append(str(event_html_id))
                missing_property = True
            if "gps_latitude" not in data_dict or "gps_longitude" not in data_dict:
                missing_gps += 1
                missing_property = True
            if "organizer" not in data_dict:
                missing_organizer += 1
                missing_property = True
            if "types" not in data_dict:
                missing_type += 1
                missing_property = True

            if missing_property:
                sth_bad += 1
            else:
                all_good += 1

        print(">> First statistics: ", end="")
        print(json.dumps({
            "events": {
                "count": len(input_events),
                "with error": error,
                "with all properties": all_good,
                "with missing property": {
                    "count": sth_bad,
                    "missing": {
                        "title": missing_title,
                        "_title_list": ', '.join(missing_title_list),
                        "perex": missing_perex,
                        "date": missing_date,
                        "_date_list": ', '.join(missing_date_list),
                        "location": missing_location,
                        "_location_list": ', '.join(missing_location_list),
                        "gps": missing_gps,
                        "organizer": missing_organizer,
                        "type": missing_type
                    }
                }
            }
        }, indent=4))

    def store_to_database(self, events_to_insert: list, dry_run: bool) -> None:
        debug_output = ""
        nok = 0
        ok = 0

        for event_data in filter(None, events_to_insert):
            data_dict, parsed_at, event_html_id = event_data
            prepared_data = self.prepare_event_data(data_dict)

            if prepared_data["status"] == "error":
                debug_output += "{} | NOK - {}\n".format(event_html_id, prepared_data["message"])
                # debug_output += "\t> {}\n".format(data_tuple)
                nok += 1
                continue

            # debug_output += "{} | OK - {}\n".format(event_html_id, prepared_data)
            ok += 1

            if not dry_run:
                query = '''INSERT OR IGNORE INTO event_data(title, perex, organizer, types, keywords,
                                                            location, gps_latitude, gps_longitude, start, end)
                           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                values = prepared_data["data"]

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    print("Error occurred when storing {} into 'event_data' table: {}".format(values, str(e)))

        self.connection.commit()

        debug_output += ">> Result: {} OKs + {} NOKs / {}\n".format(ok, nok, ok + nok)
        print(debug_output, end="")

    @staticmethod
    def prepare_event_data(data_dict: dict) -> dict:
        title = data_dict["title"][0] if "title" in data_dict else None

        if title is None:
            return {
                "status": "error",
                "message": "Title is missing!"
            }

        perex = '\n'.join(filter(None, data_dict["perex"])) if "perex" in data_dict else None
        organizer = data_dict["organizer"][0] if "organizer" in data_dict else None
        types = ','.join(filter(None, data_dict["types"])) if "types" in data_dict else None

        keywords = None  # TODO: figure out parsing of keywords

        if "location" in data_dict \
                and data_dict["location"][0] != "místo není uvedeno" \
                and data_dict["location"][0] != '\n':
            location = data_dict["location"][0]
        else:
            location = None

        gps_latitude = data_dict["gps_latitude"] if "gps_latitude" in data_dict else None  # TODO: add default GPS
        gps_longitude = data_dict["gps_longitude"] if "gps_longitude" in data_dict else None

        date_string = data_dict["date"][0] if "date" in data_dict else None
        if date_string is None or date_string == "akce není časově vymezena":
            return {
                "status": "error",
                "message": "Date is missing!"
            }

        parsed_date = ParseEvents.parse_date(date_string)
        if parsed_date is None:
            return {
                "status": "error",
                "message": "Date is not well defined!"
            }
        else:
            start, end = parsed_date

        return {
            "status": "ok",
            "data": (title, perex, organizer, types, keywords, location, gps_latitude, gps_longitude, start, end)
        }

    @staticmethod
    def parse_date(date: str) -> (str, str):
        start, _, end = date.partition('-')

        start = start.strip()
        end = end.strip()

        if not ParseEvents.is_datetime(start):
            if ParseEvents.is_datetime(start, "date"):
                start += "\xa000:00"
            else:
                return None

        start_date, _, _ = start.partition('\xa0')
        if not ParseEvents.is_datetime(end):
            if ParseEvents.is_datetime(end, "date"):
                end += "\xa023:59"
            elif ParseEvents.is_datetime(end, "time"):
                end = start_date + '\xa0' + end
            else:
                end = start_date + '\xa023:59'

        return start, end

    @staticmethod
    def is_datetime(date_string: str, partial: str = None) -> bool:
        date_split = date_string.strip().split('\xa0')

        if partial and len(date_split) == 1:
            date_strip = date_split[0].strip()

            if partial == "date" and len(date_strip.split('.')) == 3:
                return True

            if partial == "time" and len(date_strip.split(':')) == 2:
                return True

        if not partial and len(date_split) == 2:
            if ParseEvents.is_datetime(date_split[0], "date") and ParseEvents.is_datetime(date_split[1], "time"):
                return True

        return False

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
