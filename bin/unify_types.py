import argparse
import json
import multiprocessing
import re
import sqlite3
from collections import defaultdict

from lib import utils
from lib.constants import EVENT_TYPES_JSON_FILE_PATH


class UnifyTypes:

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_tables = utils.check_db_tables(self.connection,
                                                   ["event_data", "event_data_keywords", "event_data_types"])
            if len(missing_tables) != 0:
                raise Exception("Missing tables in the DB: {}".format(missing_tables))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--events-ids', type=int, nargs="*",
                            help="unify types only of the specified events' IDs")
        parser.add_argument('--unify-all', action='store_true', default=False,
                            help="reunify types even of already processed events")

        return parser.parse_args()

    def run(self):
        input_events = self._load_input_events()
        types_mapping = self._prepare_types()
        types_to_insert = self._match_types(input_events, types_mapping)
        self._store_to_db(types_to_insert)
        self.connection.close()

    def _load_input_events(self) -> dict:
        print("Loading events...")
        query = '''
                    SELECT ed.id, ed.title, ed.types, edk.keyword, edk.source
                    FROM event_data ed
                         LEFT OUTER JOIN event_data_types edt ON ed.id = edt.event_data_id
                         LEFT OUTER JOIN event_data_keywords edk ON ed.id = edk.event_data_id
                    WHERE 1 == 1
                '''

        if self.args.events_ids:
            query += ''' AND ed.id IN ({})'''.format(",".join(["{}".format(event_id)
                                                               for event_id in self.args.events_ids]))

        if not self.args.unify_all:
            query += ''' AND edt.id IS NULL'''

        cursor = self.connection.execute(query)
        event_tuples = cursor.fetchall()
        input_event_dict = {}
        for event_data_id, title, types, _, _ in event_tuples:
            input_event_dict[event_data_id] = {
                'id': event_data_id,
                'title': title,
                'types': json.loads(types) if types else [],
                'keywords': defaultdict(list)
            }
        for event_data_id, _, _, keyword, source in event_tuples:
            if source is None:
                continue
            input_event_dict[event_data_id]['keywords'][source].append(keyword)

        return input_event_dict

    @staticmethod
    def _prepare_types() -> dict:
        print("Preparing types...")
        with open(EVENT_TYPES_JSON_FILE_PATH, 'r') as types_file:
            types_list = json.load(types_file)

        types_mapping = {}
        for type_dict in types_list:
            main_type = type_dict['type']
            keywords = type_dict.get('keywords', [])
            types_mapping[main_type] = []
            for keyword in keywords:
                types_mapping[main_type].append(keyword)

        return dict(types_mapping)

    @staticmethod
    def _match_types(input_events: dict, types_mapping: dict) -> list:
        input_tuples = []
        for index, event_id in enumerate(input_events):
            input_tuples.append((index + 1, len(input_events), input_events[event_id], types_mapping))

        with multiprocessing.Pool(32) as p:
            return p.map(UnifyTypes._match_type, input_tuples)

    @staticmethod
    def _match_type(input_tuple: tuple) -> tuple:
        input_index, total_length, event_dict, types_mapping = input_tuple
        event_id = event_dict['id']

        debug_output = "{}/{} | Unifying types for event: {}".format(input_index, total_length, event_id)

        matched_types = set()
        for type_word, keywords in types_mapping.items():
            if len(event_dict['types']) != 0:
                string_to_search = "|".join(event_dict['types'])
                match = re.search(r'\b{}\b'.format(type_word.lower()), string_to_search.lower())
                if match:
                    matched_types.add(type_word)

            keywords_from_types = event_dict['keywords'].get('types', [])
            if UnifyTypes._type_matches_keywords(types_mapping[type_word], keywords_from_types):
                matched_types.add(type_word)

        if len(matched_types) == 0:
            debug_output += " - Guessing type from keywords..."
            if len(event_dict['keywords']) != 0:
                for type_word, keywords in types_mapping.items():
                    keywords_from_title = event_dict['keywords'].get('title', [])
                    if UnifyTypes._type_matches_keywords(types_mapping[type_word], keywords_from_title):
                        matched_types.add(type_word)

        print(debug_output)
        return event_id, list(matched_types), event_dict['types']

    @staticmethod
    def _type_matches_keywords(type_keywords, event_keywords) -> bool:
        for keyword in event_keywords:
            if keyword in type_keywords:
                return True
        return False

    def _store_to_db(self, types_to_insert: list) -> None:
        print("Inserting into DB...")
        events_without_type = []
        result_dict = {}
        nok = 0

        for event_data_id, types, old_types in types_to_insert:
            result_dict[event_data_id] = {
                'original_types': old_types,
                'matched_types': types
            }
            values = []
            if len(types) == 0:
                nok += 1
                events_without_type.append(event_data_id)
                values = ['({}, {})'.format("null", str(event_data_id))]
            else:
                for event_type in types:
                    values.append('("{}", {})'.format(event_type, str(event_data_id)))

            if not self.args.dry_run:
                query = '''
                            INSERT OR IGNORE INTO event_data_types(type, event_data_id)
                            VALUES {}
                        '''.format(', '.join(values))
                try:
                    self.connection.execute(query)
                except sqlite3.Error as e:
                    print("Error occurred when storing {} into 'event_data_types' table: {}".format(values, str(e)))
        if self.args.dry_run:
            print(json.dumps(result_dict, indent=4, ensure_ascii=False))
        else:
            self.connection.commit()

        print(">> Result: {} OKs + {} NOKs / {}".format(len(types_to_insert) - nok, nok, len(types_to_insert)))
        print(">> Events without type's event_data IDs: {}".format(events_without_type))


if __name__ == '__main__':
    unify_types = UnifyTypes()
    unify_types.run()
