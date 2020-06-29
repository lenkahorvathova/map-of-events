import argparse
import multiprocessing
import os
import sqlite3
import sys
from datetime import datetime

from lib import utils
from lib.constants import DATA_DIR_PATH


class DownloadEvents:
    """ Downloads an HTML content of an event's page.

    Stores event's information into the database.
    """

    EVENTS_FOLDER_NAME = "events"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_tables = utils.check_db(self.connection, ["calendar", "event_url", "event_html"])
            if len(missing_tables) != 0:
                raise Exception("Missing tables in the DB: {}".format(missing_tables))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="download events only for the specified domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="download only event with the specified URL")
        parser.add_argument('--redownload-file', action='store_true', default=False,
                            help="redownload file for the specified URL in --event-url")  # not updating parsed_at

        arguments = parser.parse_args()
        if arguments.redownload_file and not arguments.event_url:
            parser.error("--redownload-file requires --event-url")

        return arguments

    def run(self) -> None:
        input_events = self.load_input_events()
        events_to_insert = self.download_events(input_events)
        if self.args.redownload_file:
            _, html_file_path, _ = events_to_insert[0]
            print("File was re-downloaded to: {}".format(html_file_path))
        else:
            self.store_to_database(events_to_insert, self.args.dry_run)
        self.connection.close()

    def load_input_events(self) -> list:
        print("Loading input events...")
        query = '''SELECT eu.id, eu.url, c.url FROM event_url eu
                   LEFT OUTER JOIN event_html eh ON eu.id = eh.event_url_id
                   INNER JOIN calendar c ON eu.calendar_id = c.id
                   WHERE 1==1'''

        if self.args.domain:
            website_base = utils.get_base_by("domain", self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base["url"]
            query += ''' AND c.url = "{}"'''.format(calendar_url)

        if self.args.event_url:
            query += ''' AND eu.url = "{}"'''.format(self.args.event_url)

        if not self.args.redownload_file:
            query += ''' AND eh.event_url_id IS NULL'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def download_events(self, input_events: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, event in enumerate(input_events):
            _, _, calendar_url = event
            website_base = utils.get_base_by("url", calendar_url)
            if website_base is None:
                sys.exit("Unknown calendar URL '{}'!".format(calendar_url))

            input_tuples.append((index + 1, len(input_events), event, timestamp, website_base, self.args.dry_run))

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadEvents.process_event_url, input_tuples)

    @staticmethod
    def process_event_url(input_tuple: tuple) -> (int, str, str):
        input_index, total_length, event, timestamp, website_base, dry_run = input_tuple
        """ (input_index: int, total_length: int, event: (int, str, str), timestamp: datetime, website_base: dict,
            dry_run: bool) """
        event_id, event_url, _ = event

        current_dir = os.path.join(DATA_DIR_PATH, website_base["domain"])
        event_file_dir = os.path.join(current_dir, DownloadEvents.EVENTS_FOLDER_NAME)
        os.makedirs(event_file_dir, exist_ok=True)

        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        event_file_name = timestamp_str + "_" + str(event_id)
        html_file_path = os.path.join(event_file_dir, event_file_name + ".html")

        result = utils.download_html_content(event_url, html_file_path, website_base.get("encoding", None), dry_run)
        if result != "200":
            html_file_path = None

        debug_output = "{}/{}".format(input_index, total_length)
        debug_output += " | Downloading URL: {} | {}".format(str(event_url), str(result))
        print(debug_output)

        return event_id, html_file_path, timestamp

    def store_to_database(self, events_to_insert: list, dry_run: bool) -> None:
        failed_url_ids = []
        event_url_ids = []

        for event_info in events_to_insert:
            event_url_id, html_file_path, downloaded_at = event_info
            event_url_ids.append(event_url_id)

            if html_file_path is None:
                failed_url_ids.append(event_url_id)
                continue

            if not dry_run:
                query = '''INSERT INTO event_html(html_file_path, downloaded_at, event_url_id)
                           VALUES(?, ?, ?)'''
                values = (html_file_path, downloaded_at, event_url_id)

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    failed_url_ids.append(event_url_id)
                    print("Error occurred when storing {} into 'event_html' table: {}".format(values, str(e)))
        if not dry_run:
            self.connection.commit()

        print(">> Number of failed events: {}/{}".format(len(failed_url_ids), len(event_url_ids)))
        print(">> Failed events' IDs: {}".format(failed_url_ids))


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
