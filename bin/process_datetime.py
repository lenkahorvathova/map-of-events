import argparse
import json
import logging
import multiprocessing
import sqlite3
import sys
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import SIMPLE_LOGGER_PREFIX
from lib.datetime_parser import DatetimeParser


class ProcessDatetime:
    """ Processes datetime of parsed events. """

    def __init__(self):
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection,
                                  ["calendar", "event_url", "event_html", "event_data", "event_data_datetime"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Processes datetime of parsed events.")
        parser.add_argument('--domain', type=str, default=None,
                            help="process datetime only of events from the specified calendar domain")
        parser.add_argument('--event-url', type=str, default=None,
                            help="process datetime only of an event from the specified URL")
        parser.add_argument('--events-ids', type=int, nargs="*",
                            help="process datetime only of events with the specified event_data IDs")
        parser.add_argument('--process-all', action='store_true', default=False,
                            help="process datetime of even already processed events")
        return parser.parse_args()

    def run(self) -> None:
        input_events = self._load_input_events()
        datetimes_to_insert = self._process_datetimes(input_events)
        self._store_to_database(datetimes_to_insert)
        self.connection.close()

    def _load_input_events(self) -> List[tuple]:
        self.logger.info("Loading input events...")

        query = '''
                    SELECT ed.id, ed.datetime, 
                           eu.url, 
                           c.url
                    FROM event_data ed
                         INNER JOIN event_html eh ON ed.event_html_id = eh.id
                         INNER JOIN event_url eu ON eh.event_url_id = eu.id
                         INNER JOIN calendar c ON eu.calendar_id = c.id
                    WHERE 1 == 1
                '''

        if not self.args.process_all:
            query += ''' AND ed.id NOT IN (SELECT DISTINCT event_data_id FROM event_data_datetime)'''

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

        if self.args.events_ids:
            query += ''' AND ed.id IN ({})'''.format(",".join(["{}".format(event_id)
                                                               for event_id in self.args.events_ids]))

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def _process_datetimes(self, input_events: List[tuple]) -> List[tuple]:
        self.logger.info("Processing events' datetimes...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__, log_file=self.args.log_file, debug=self.args.debug)

        input_tuples = []
        for index, event_tuple in enumerate(input_events):
            _, _, _, calendar_url = event_tuple
            website_base = utils.get_base_by_url(calendar_url)
            input_tuples.append((index + 1, len(input_events), event_tuple, website_base))

        with multiprocessing.Pool(32) as p:
            return p.map(ProcessDatetime._process_datetimes_process, input_tuples)

    @staticmethod
    def _process_datetimes_process(input_tuple: (int, int, (int, str, str, str), dict)) -> (List[tuple], int):
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, event_tuple, website_base = input_tuple
        event_data_id, event_data_datetime, event_url, _ = event_tuple
        db_datetimes = list(json.loads(event_data_datetime)) if event_data_datetime else []

        info_output = "{}/{} | Processing datetime of: {}".format(input_index, total_length, event_url)

        if len(db_datetimes) == 0:
            simple_logger.warning(info_output + " | NOK - (Event has no datetime!)")
            return [], event_data_id

        parser = DatetimeParser(website_base["parser"])
        try:
            processed_datetimes = parser.process_datetimes(db_datetimes)
        except Exception as e:
            simple_logger.error(info_output + " | NOK (Exception: {})".format(str(e)))
            if len(parser.error_messages) != 0:
                simple_logger.debug("Parser's errors: {}".format(json.dumps(parser.error_messages, indent=4)))
            return [], event_data_id

        if len(processed_datetimes) == 0:
            simple_logger.warning(info_output + " | 0")
        else:
            simple_logger.info(info_output + " | {}".format(len(processed_datetimes)))
        if len(parser.error_messages) != 0:
            simple_logger.debug("Parser's errors: {}".format(json.dumps(parser.error_messages, indent=4)))

        return processed_datetimes, event_data_id

    def _store_to_database(self, datetimes_to_insert: List[tuple]) -> None:
        if not self.args.dry_run:
            self.logger.info("Inserting into DB...")

        milestones = [10, 30, 50, 70, 90, 100]
        nok = []
        for index, dt_tuple in enumerate(datetimes_to_insert):
            processed_datetimes, event_data_id = dt_tuple

            if not processed_datetimes:
                nok.append(event_data_id)
                processed_datetimes = [(None, None, None, None)]

            tuples_to_insert = [tpl + (event_data_id,) for tpl in processed_datetimes]
            tuples_to_insert = ", ".join([tpl.__str__().replace('None', 'null') for tpl in set(tuples_to_insert)])

            if not self.args.dry_run:
                curr_percentage = (index + 1) / len(datetimes_to_insert) * 100
                while len(milestones) > 0 and curr_percentage >= milestones[0]:
                    self.logger.debug("...{:.0f} % inserted".format(milestones[0]))
                    milestones = milestones[1:]

                query = '''
                            INSERT OR IGNORE INTO event_data_datetime(start_date, start_time, end_date, end_time, event_data_id)
                            VALUES {}
                        '''.format(tuples_to_insert)
                try:
                    self.connection.execute(query)
                except sqlite3.Error as e:
                    nok.append(event_data_id)
                    self.logger.error(
                        "Error occurred when storing {} into 'event_data_datetime' table: {}".format(tuples_to_insert,
                                                                                                     str(e)))
                    continue
            if not self.args.dry_run:
                self.connection.commit()

        self.logger.info(">> Result: {} OKs + {} NOKs / {}".format(len(datetimes_to_insert) - len(nok), len(nok),
                                                                   len(datetimes_to_insert)))
        self.logger.info(">> Failed event_data IDs: {}".format(nok))


if __name__ == '__main__':
    process_datetime = ProcessDatetime()
    process_datetime.run()
