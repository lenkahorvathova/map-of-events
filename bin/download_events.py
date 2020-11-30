import argparse
import json
import logging
import multiprocessing
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import DATA_DIR_PATH, SIMPLE_LOGGER_PREFIX


class DownloadEvents:
    """ Downloads an event's page HTML content of found events' URLs. """

    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection, ["calendar", "event_url", "event_html"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Downloads an event's page HTML content of found events' URLs.")
        parser.add_argument('--domain', type=str, default=None,
                            help="download events only from the specified calendar domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="download only event with the specified URL")
        parser.add_argument('--redownload-file', action='store_true', default=False,
                            help="redownload content of the specified URL in --event-url; doesn't update the database")

        arguments = parser.parse_args()
        if arguments.redownload_file and not arguments.event_url:
            parser.error("--redownload-file requires --event-url")

        return arguments

    def run(self) -> None:
        input_events = self._load_input_events()
        events_to_insert = self._download_events(input_events)
        self._store_to_database(events_to_insert)
        self.connection.close()

    def _load_input_events(self) -> List[tuple]:
        self.logger.info("Loading input events...")

        query = '''
                    SELECT eu.id, eu.url,
                           c.url
                    FROM event_url eu
                         LEFT OUTER JOIN event_html eh ON eu.id = eh.event_url_id
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

        if not self.args.redownload_file:
            query += ''' AND eh.event_url_id IS NULL'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def _download_events(self, input_events: List[tuple]) -> List[tuple]:
        self.logger.info("Downloading events...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__, log_file=self.args.log_file, debug=self.args.debug)
        timestamp = datetime.now()
        input_tuples = []
        for index, event in enumerate(input_events):
            _, _, calendar_url = event
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_events), event, timestamp, website_base, self.args.dry_run))
        random.shuffle(input_tuples)

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadEvents._download_events_process, input_tuples)

    @staticmethod
    def _download_events_process(input_tuple: (int, int, (int, str, str), datetime, dict, bool)) -> (
            int, str, datetime, str):
        time.sleep(round(random.uniform(0, 5), 2))
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, event, timestamp, website_base, dry_run = input_tuple
        event_id, event_url, _ = event

        current_dir = os.path.join(DATA_DIR_PATH, website_base["domain"])
        event_file_dir = os.path.join(current_dir, DownloadEvents.EVENTS_FOLDER_NAME)
        event_file_name = timestamp.strftime("%Y-%m-%d_%H-%M-%S") + "_" + str(event_id)
        html_file_path = os.path.join(event_file_dir, event_file_name + ".html")

        os.makedirs(event_file_dir, exist_ok=True)
        result = utils.download_html_content(event_url, html_file_path,
                                             encoding=website_base.get("encoding", None),
                                             verify=website_base.get("verify", None), dry_run=dry_run)
        if result != "200":
            html_file_path = None

        simple_logger.info(
            "{}/{} | Downloading URL: {} | {}".format(input_index, total_length, str(event_url), str(result)))

        return event_id, html_file_path, timestamp, result

    def _store_to_database(self, events_to_insert: List[tuple]) -> None:
        if self.args.redownload_file:
            if not self.args.dry_run:
                _, html_file_path, _ = events_to_insert[0]
                self.logger.info("File was redownloaded to: {}".format(html_file_path))
            return

        if not self.args.dry_run:
            self.logger.info("Inserting into DB...")

        error_dict = defaultdict(int)
        failed_url_ids = []
        event_url_ids = []
        for event_info in events_to_insert:
            event_url_id, html_file_path, downloaded_at, status_code = event_info
            event_url_ids.append(event_url_id)
            error_dict[status_code] += 1

            if html_file_path is None:
                failed_url_ids.append(event_url_id)

            if not self.args.dry_run:
                query = '''
                            INSERT INTO event_html(html_file_path, downloaded_at, event_url_id)
                            VALUES(?, ?, ?)
                        '''
                values = (html_file_path, downloaded_at, event_url_id)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    failed_url_ids.append(event_url_id)
                    self.logger.error(
                        "Error occurred when storing {} into 'event_html' table: {}".format(values, str(e)))
        if not self.args.dry_run:
            self.connection.commit()

        self.logger.debug(">> Error stats: {}".format(json.dumps(error_dict, indent=4)))
        self.logger.info(">> Number of failed events: {}/{}".format(len(failed_url_ids), len(event_url_ids)))
        self.logger.info(">> Failed event_url IDs: {}".format(failed_url_ids))


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
