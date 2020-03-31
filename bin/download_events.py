import argparse
import multiprocessing
import os
import sqlite3
import sys
from datetime import datetime

from lib import utils
from lib.constants import DATA_DIR_PATH


class DownloadEvents:
    """ Downloads an HTML content of an event page.

    Stores event's information into the database.
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
                            help="download events only for the specified domain")  # TODO: Fix!

        return parser.parse_args()

    def run(self) -> None:
        input_events = self.load_input_events()
        events_to_insert = self.download_events(input_events)
        self.store_to_database(events_to_insert, self.args.dry_run)
        self.connection.close()

    def load_input_events(self) -> list:
        print("Loading input events...")
        query = '''SELECT eu.id, eu.url FROM event_url eu
                   LEFT OUTER JOIN event_html eh ON eu.id = eh.event_url_id
                   WHERE eh.event_url_id IS NULL'''

        if self.args.domain:
            website_base = utils.get_base_by("domain", self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base["url"]

            cursor = self.connection.execute('''SELECT id FROM calendar WHERE url == "{}"'''.format(calendar_url))
            calendar_ids = [id[0] for id in cursor.fetchall()]
            query += " AND eu.calendar_id IN ({})".format(",".join(['"{}"'.format(id) for id in calendar_ids]))

        cursor = self.connection.execute(query)

        return cursor.fetchall()

    def download_events(self, input_events: list) -> list:
        timestamp = datetime.now()
        input_tuples = []

        for index, event in enumerate(input_events):
            _, event_url = event
            domain = utils.generate_domain_name(event_url)
            input_tuples.append((index + 1, len(input_events), event, timestamp, domain, self.args.dry_run))

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadEvents.process_event_url, input_tuples)

    @staticmethod
    def process_event_url(input_tuple: tuple) -> (int, str, str):
        input_index, total_length, event, timestamp, domain, dry_run = input_tuple
        """ (input_index: int, total_length: int, event: (int, str), timestamp: datetime, domain: str, 
            dry_run: bool) """
        event_id, event_url = event

        current_dir = os.path.join(DATA_DIR_PATH, domain)
        event_file_dir = os.path.join(current_dir, DownloadEvents.EVENTS_FOLDER_NAME)
        os.makedirs(event_file_dir, exist_ok=True)

        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        event_file_name = timestamp_str + "_" + str(event_id)
        html_file_path = os.path.join(event_file_dir, event_file_name + ".html")

        result = utils.download_html_content(event_url, html_file_path, dry_run)
        if result != "200":
            html_file_path = None

        debug_output = "{}/{} | ".format(input_index, total_length)
        debug_output += "Downloading URL: " + str(event_url) + " (" + str(result) + ")"
        print(debug_output)

        return event_id, html_file_path, timestamp

    def store_to_database(self, events_to_insert: list, dry_run: str) -> None:
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
                    print("Error occurred when storing {} into 'event_url' table: {}".format(values, str(e)))

        if not dry_run:
            self.connection.commit()

        print("Number of failed events: {}/{}".format(len(failed_url_ids), len(event_url_ids)))
        print("Failed events' IDs: {}".format(failed_url_ids))


if __name__ == '__main__':
    download_events = DownloadEvents()
    download_events.run()
