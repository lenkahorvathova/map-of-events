import argparse
import json
import logging
import multiprocessing
import re
import sqlite3
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import SIMPLE_LOGGER_PREFIX


class ExtractKeywords:
    """ Extract keywords of parsed events. """

    EVENT_KEYWORDS_JSON_FILE_PATH = "resources/event_keywords.json"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection, ["event_data", "event_data_keywords"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.add_argument('--events-ids', type=int, nargs="*",
                            help="extract keywords only from events with the specified event_data IDs")
        parser.add_argument('--extract-all', action='store_true', default=False,
                            help="extract keywords even from already processed events")
        return parser.parse_args()

    def run(self) -> None:
        input_events = self._load_input_events()
        keywords_dict = self._prepare_keywords_dict()
        keywords_to_insert = self._extract_keywords(input_events, keywords_dict)
        self._store_to_db(keywords_to_insert)
        self.connection.close()

    def _load_input_events(self) -> List[tuple]:
        self.logger.info("Loading input events...")

        query = '''
                    SELECT ed.id, ed.title, ed.perex, ed.types
                    FROM event_data ed
                         LEFT OUTER JOIN event_data_keywords edk ON ed.id = edk.event_data_id
                    WHERE 1 == 1
                '''

        if self.args.events_ids:
            query += ''' AND ed.id IN ({})'''.format(",".join(["{}".format(event_id)
                                                               for event_id in self.args.events_ids]))

        if not self.args.extract_all:
            query += ''' AND edk.id IS NULL'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def _prepare_keywords_dict(self) -> dict:
        self.logger.info("Preparing custom keywords...")

        with open(ExtractKeywords.EVENT_KEYWORDS_JSON_FILE_PATH, 'r') as keywords_file:
            keywords_mapping = json.load(keywords_file)
            for keyword in keywords_mapping:
                keywords_mapping[keyword].append(keyword)
            return dict(keywords_mapping)

    def _extract_keywords(self, input_events: List[tuple], keywords_dict: dict) -> List[tuple]:
        self.logger.info("Extracting events' keywords...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__, log_file=self.args.log_file, debug=self.args.debug)
        input_tuples = []
        for index, event in enumerate(input_events):
            input_tuples.append((index + 1, len(input_events), event, keywords_dict))

        with multiprocessing.Pool(32) as p:
            return p.map(ExtractKeywords._extract_keywords_process, input_tuples)

    @staticmethod
    def _extract_keywords_process(input_tuple: (int, int, (int, str, str, str),
                                                dict)) -> (int, List[tuple], str, str, str):
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, event, keywords_dict = input_tuple
        event_data_id, title, perex, types = event

        info_output = "{}/{} | Extracting keywords from: {}".format(input_index, total_length, event_data_id)

        matched_keywords = set()
        event_data = {
            "title": title,
            "perex": perex,
            "types": types
        }
        for source, string_to_search in event_data.items():
            if string_to_search is None:
                continue

            for keyword, stemmed_list in keywords_dict.items():
                for stemmed_word in stemmed_list:
                    word_count = len(stemmed_word.split())
                    if word_count > 1:
                        matched = False
                        multiword = stemmed_word.split()
                        word_rest_count = word_count - 1
                        regex_pattern = r'\b{}\w*'.format(multiword[0].lower()) + word_rest_count * r'\s*(\w*)'
                        match_iter = re.finditer(regex_pattern, string_to_search.lower())
                        for match in match_iter:
                            matched = True
                            for i in range(word_rest_count):
                                next_word_match = re.search(r'\b{}'.format(multiword[i + 1].lower()),
                                                            match.group(i + 1))
                                if next_word_match is None:
                                    matched = False
                        if matched:
                            matched_keywords.add((keyword, source))
                    else:
                        match = re.search(r'\b{}'.format(stemmed_word.lower()), string_to_search.lower())
                        if match:
                            matched_keywords.add((keyword, source))

        if len(matched_keywords) == 0:
            simple_logger.warning(info_output + " | NOK")
        else:
            simple_logger.info(info_output + " | OK")

        return event_data_id, list(matched_keywords), title, perex, types

    def _store_to_db(self, keywords_to_insert: List[tuple]) -> None:
        self.logger.info("Inserting into DB...")

        events_without_keywords = []
        results = {}
        nok = 0
        for event_data_id, matched_keywords, title, perex, types in keywords_to_insert:
            results[event_data_id] = {
                'title': title,
                'perex': perex,
                'types': types,
                'matched_keywords': matched_keywords
            }
            values = []
            if len(matched_keywords) == 0:
                nok += 1
                events_without_keywords.append(event_data_id)
                values = ['({}, {}, {})'.format("null", "null", str(event_data_id))]
            else:
                for event_keyword, source in matched_keywords:
                    values.append('("{}", "{}", {})'.format(event_keyword, source, str(event_data_id)))

            if not self.args.dry_run:
                query = '''
                            INSERT OR IGNORE INTO event_data_keywords(keyword, source, event_data_id)
                            VALUES {}
                        '''.format(', '.join(values))
                try:
                    self.connection.execute(query)
                except sqlite3.Error as e:
                    self.logger.error(
                        "Error occurred when storing {} into 'event_data_types' table: {}".format(values, str(e)))
        if self.args.dry_run:
            print(json.dumps(results, indent=4, ensure_ascii=False))
        else:
            self.connection.commit()

        self.logger.info(">> Result: {} OKs + {} NOKs / {}".format(len(keywords_to_insert) - nok, nok,
                                                                   len(keywords_to_insert)))
        self.logger.info(">> Events without keywords's event_data IDs: {}".format(events_without_keywords))


if __name__ == '__main__':
    extract_keywords = ExtractKeywords()
    extract_keywords.run()
