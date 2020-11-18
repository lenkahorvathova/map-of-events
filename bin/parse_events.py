import argparse
import json
import logging
import multiprocessing
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from typing import List

from lxml import etree

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import SIMPLE_LOGGER_PREFIX
from lib.parser import Parser


class ParseEvents:
    """ Parses a downloaded event's page HTML content for events' detail information. """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection, ["calendar", "event_url", "event_html", "event_data"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Parses a downloaded event's page HTML content for events' detail information.")
        parser.add_argument('--domain', type=str, default=None,
                            help="parse events only of the specified calendar domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="parse data only of the specified event URL")
        parser.add_argument('--parse-all', action='store_true', default=False,
                            help="parse even already parsed events")

        arguments = parser.parse_args()
        if arguments.domain and not arguments.dry_run:
            parser.error("--domain requires --dry-run")
        if arguments.event_url and not arguments.dry_run:
            parser.error("--event-url requires --dry-run")
        if arguments.parse_all and not arguments.dry_run:
            parser.error("--parse-all requires --dry-run")

        return arguments

    def run(self) -> None:
        input_events = self._load_input_events()
        events_to_insert = self._parse_events(input_events)
        self._store_to_database(events_to_insert)
        self._update_database(input_events)
        self.connection.close()

    def _load_input_events(self) -> List[tuple]:
        self.logger.info("Loading input events...")

        query = '''
                    SELECT eh.id, eh.html_file_path, 
                           eu.url, 
                           c.url
                    FROM event_html eh
                         INNER JOIN event_url eu ON eh.event_url_id = eu.id
                         INNER JOIN calendar c ON eu.calendar_id = c.id
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
            query += ''' AND c.url = "{}"'''.format(calendar_url)

        if self.args.event_url:
            query += ''' AND eu.url = "{}"'''.format(self.args.event_url)

        if not self.args.parse_all:
            query += ''' AND eh.is_parsed == 0'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def _parse_events(self, input_events: List[tuple]) -> List[tuple]:
        self.logger.info("Parsing events...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__, log_file=self.args.log_file, debug=self.args.debug)
        timestamp = datetime.now()
        input_tuples = []
        for index, event_tuple in enumerate(input_events):
            _, _, _, calendar_url = event_tuple
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_events), event_tuple, timestamp, website_base))

        with multiprocessing.Pool(32) as p:
            return p.map(ParseEvents._parse_events_process, input_tuples)

    @staticmethod
    def _parse_events_process(input_tuple: (int, int, (int, str, str, str), datetime, dict)) -> (dict, datetime, tuple):
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, event_tuple, timestamp, website_base = input_tuple
        event_html_id, event_html_file_path, event_url, _ = event_tuple

        info_output = "{}/{} | Parsing event: {}".format(input_index, total_length, event_url)

        if not event_html_file_path:
            simple_logger.error(info_output + " | NOK - (File path for the event '{}' is None!)".format(event_url))
            return {"error": "Filepath is None!"}, timestamp, event_tuple

        elif not os.path.isfile(event_html_file_path):
            simple_logger.error(info_output + " | NOK - (File '{}' does not exist!)".format(event_html_file_path))
            return {"error": "File does not exist!"}, timestamp, event_tuple

        with open(event_html_file_path, encoding="utf-8") as html_file:
            dom = etree.parse(html_file, etree.HTMLParser(encoding="utf-8"))

        parser = Parser(website_base["parser"])
        parser.set_dom(dom)

        try:
            parsed_event_data = parser.get_event_data()
        except Exception as e:
            simple_logger.error(info_output + " | NOK (Exception: {})".format(str(e)))
            if len(parser.error_messages) != 0:
                simple_logger.debug("Parser's errors: {}".format(json.dumps(parser.error_messages, indent=4)))
            return {"error": "Exception occurred during parsing!"}, timestamp, event_tuple

        if len(parsed_event_data) == 0:
            simple_logger.error(info_output + " | NOK")
            if len(parser.error_messages) != 0:
                simple_logger.debug("Parser's errors: {}".format(json.dumps(parser.error_messages, indent=4)))
            return {"error": "No data were parsed!"}, timestamp, event_tuple

        simple_logger.info(info_output + " | OK")
        if len(parser.error_messages) != 0:
            simple_logger.debug("Parser's errors: {}".format(json.dumps(parser.error_messages, indent=4)))

        return parsed_event_data, timestamp, event_tuple

    def _store_to_database(self, events_to_insert: List[tuple]) -> None:
        if not self.args.dry_run:
            self.logger.info("Inserting into DB...")

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

            if not self.args.dry_run:
                query = '''
                            INSERT INTO event_data(title, perex, datetime, location, gps, organizer, types, event_html_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                values = (data_dict.get("title"), data_dict.get("perex", None), data_dict.get("datetime"),
                          data_dict.get("location", None), data_dict.get("gps", None), data_dict.get("organizer", None),
                          data_dict.get("types", None), event_html_id)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    self.logger.error(
                        "Error occurred when storing {} into 'event_data' table: {}".format(values, str(e)))
                    nok_list.append(event_html_id)
                    error_dict["Error occurred during storing!"] += 1
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
        if self.args.dry_run:
            print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
        else:
            self.connection.commit()

        if len(error_dict) > 0:
            self.logger.info(">> Errors stats: {}".format(json.dumps(error_dict, indent=4, ensure_ascii=False)))
        self.logger.info(">> Result: {} OKs + {} NOKs / {}".format(ok, len(nok_list), ok + len(nok_list)))
        self.logger.info(">> Failed event_html IDs: {}".format(nok_list))

    def _update_database(self, input_events: List[tuple]) -> None:
        if self.args.dry_run:
            return

        self.logger.info("Updating DB...")

        input_ids = [event[0] for event in input_events]
        query = '''
                    UPDATE event_html
                    SET is_parsed = 1
                    WHERE id IN ({})
                '''.format(",".join(['"{}"'.format(calendar_id) for calendar_id in input_ids]))

        try:
            self.connection.execute(query)
        except sqlite3.Error as e:
            self.logger.error("Error occurred when updating 'is_parsed' in 'event_html' table: {}".format(str(e)))
        self.connection.commit()


if __name__ == '__main__':
    parse_events = ParseEvents()
    parse_events.run()
