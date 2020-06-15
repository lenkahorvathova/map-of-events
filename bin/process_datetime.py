import argparse
import json
import multiprocessing
import sqlite3
import sys

from lib import utils
from lib.parser import Parser


class ProcessDatetime:
    def __init__(self):
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="process datetime only of the specified domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="process datetime only of the specified URL")

        return parser.parse_args()

    def run(self) -> None:
        input_events = self.load_events()
        datetimes_to_insert = self.process_datetimes(input_events)
        self.store_to_database(datetimes_to_insert, self.args.dry_run)
        self.connection.close()

    def load_events(self) -> list:
        print("Loading input events...")
        query = '''SELECT ed.id, ed.datetime, eu.url, c.url FROM event_data ed
                   INNER JOIN event_html eh on ed.event_html_id = eh.id 
                   INNER JOIN event_url eu ON eh.event_url_id = eu.id 
                   INNER JOIN calendar c ON eu.calendar_id = c.id 
                   WHERE ed.id NOT IN (SELECT DISTINCT event_data_id FROM event_data_datetime)'''

        if self.args.domain:
            website_base = utils.get_base_by("domain", self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base["url"]
            query += ''' AND c.url = "{}"'''.format(calendar_url)

        if self.args.event_url:
            query += ''' AND eu.url = "{}"'''.format(self.args.event_url)

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def process_datetimes(input_events: list) -> list:
        input_tuples = []

        for index, event_tuple in enumerate(input_events):
            _, _, _, calendar_url = event_tuple
            website_base = utils.get_base_by("url", calendar_url)
            input_tuples.append((index + 1, len(input_events), event_tuple, website_base))

        with multiprocessing.Pool(32) as p:
            return p.map(ProcessDatetime.process_datetime, input_tuples)

    @staticmethod
    def process_datetime(input_tuple: tuple):
        input_index, total_length, event_tuple, website_base = input_tuple
        event_data_id, event_data_datetime, event_url, _ = event_tuple

        debug_output = "{}/{} | Processing datetime of: {}".format(input_index, total_length, event_url)

        if event_data_datetime is None:
            debug_output += " | NOK - (Event's datetime is None!)"
            print(debug_output)
            return [], event_data_id

        parser_name = website_base["parser"]
        parser = Parser(parser_name)

        db_datetimes = list(json.loads(event_data_datetime))
        try:
            processed_datetimes = parser.process_datetimes(db_datetimes)
        except Exception as e:
            debug_output += " | NOK"
            if len(parser.error_messages) != 0:
                debug_output += " - ({})".format(" & ".join(parser.error_messages))
            debug_output += "\n\t> Exception: {}".format(str(e))
            print(debug_output)
            return [], event_data_id

        debug_output += " | {}".format(len(processed_datetimes))
        print(debug_output)

        return processed_datetimes, event_data_id

    def store_to_database(self, datetimes_to_insert: list, dry_run: bool) -> None:
        print("Inserting processed datetimes into DB...")
        ok = 0
        nok = 0

        for dt_tuple in datetimes_to_insert:
            processed_datetimes, event_data_id = dt_tuple

            if not processed_datetimes:
                nok += 1
                processed_datetimes = [(None, None, None, None)]

            tuples_to_insert = [tpl + (event_data_id,) for tpl in processed_datetimes]
            tuples_to_insert = ", ".join([tpl.__str__().replace('None', 'null') for tpl in set(tuples_to_insert)])

            if not dry_run:
                query = '''INSERT INTO event_data_datetime(start_date, start_time, end_date, end_time, event_data_id)
                           VALUES {}'''.format(tuples_to_insert)

                try:
                    self.connection.execute(query)
                except sqlite3.Error as e:
                    nok += 1
                    print("Error occurred when storing {} into 'event_data_datetime' table: {}".format(
                        tuples_to_insert, str(e)))
                    continue

            ok += 1
            self.connection.commit()

        print(">> Result: {} OKs + {} NOKs / {}".format(ok, nok, ok + nok))


if __name__ == '__main__':
    process_datetime = ProcessDatetime()
    process_datetime.run()
