import argparse
import math
import multiprocessing
import re
import sqlite3
from collections import defaultdict

from lib import utils


class DeduplicateEvents:
    CANCELLED_REGEX = re.compile(r'\b(zrušen|ZRUŠEN|Zrušen)')
    DEFERRED_REGEX = re.compile(r'\b(odložen|ODLOŽEN|Odložen|přesunut|PŘESUNUT|Přesunut)')
    IS_WORD_REGEX = re.compile(r'\b\w[^\s]+\b')
    SPECIAL_CHARACTER_REGEX = re.compile(r'([\W+])')

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_views = utils.check_db_views(self.connection, ["event_data_view"])
            if len(missing_views) != 0:
                raise Exception("Missing views in the DB: {}".format(missing_views))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--event-url', type=str, default=None,
                            help="find duplicates of the specified URL")
        parser.add_argument('--deduplicate-all', action='store_true', default=False,
                            help="deduplicate all events in the database")

        return parser.parse_args()

    def run(self) -> None:
        all_events = self._get_input_events()
        duplicates_to_mark = self._find_duplicates(self.args.event_url, all_events)
        self._update_database(duplicates_to_mark, self.args.dry_run)
        self.connection.close()

    def _get_input_events(self) -> dict:
        print("Loading events...")
        query = '''
                    SELECT calendar__url, calendar__downloaded_at,
                           event_url__id, event_url__url,
                           event_data__title, event_data__perex, event_data__location, event_data__gps, event_data__organizer,
                           event_data_datetime__start_date, event_data_datetime__start_time, event_data_datetime__end_date, event_data_datetime__end_time,
                           event_data_gps__online, event_data_gps__has_default, event_data_gps__gps, event_data_gps__location, event_data_gps__municipality, event_data_gps__district,
                           event_data_keywords__keyword,
                           event_data_types__type
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL 
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                '''

        if not self.args.deduplicate_all:
            query += ''' AND (event_data_datetime__start_date >= date('now') OR (event_data_datetime__end_date IS NOT NULL AND event_data_datetime__end_date >= date('now')))
                         AND event_url__duplicate_of IS NULL
                     '''

        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.execute(query)
        fetched_events = [dict(row) for row in cursor.fetchall()]
        calendars_base = utils.get_base_dict_per_url()

        result_events = {}
        for event_dict in fetched_events:
            event_url = event_dict['event_url__url']
            calendar_url = event_dict['calendar__url']

            datetime_tuple = event_dict['event_data_datetime__start_date'], \
                             event_dict['event_data_datetime__start_time'], \
                             event_dict['event_data_datetime__end_date'], \
                             event_dict['event_data_datetime__end_time']
            event_keyword = event_dict['event_data_keywords__keyword']
            event_type = event_dict['event_data_types__type']

            if event_url in result_events:
                result_events[event_url]['datetimes'].add(datetime_tuple)
                if event_keyword is not None:
                    result_events[event_url]['keywords'].add(event_keyword)
                if event_type:
                    result_events[event_url]['types'].add(event_type)
            else:
                gps = None
                if event_dict['event_data__gps'] is not None:
                    gps = event_dict['event_data__gps']
                elif event_dict['event_data_gps__gps'] is not None:
                    gps = event_dict['event_data_gps__gps']

                if event_dict['event_data_gps__has_default'] == 0:
                    geocoded_location = "{}, {}".format(event_dict['event_data_gps__municipality'],
                                                        event_dict['event_data_gps__district'])
                else:
                    geocoded_location = calendars_base[calendar_url].get('default_location', None)

                result_events[event_url] = {
                    'url': event_url,
                    'id': event_dict['event_url__id'],
                    'calendar_url': calendar_url,
                    'downloaded_at': event_dict['calendar__downloaded_at'],
                    'title': event_dict['event_data__title'],
                    'perex': event_dict['event_data__perex'],
                    'location': event_dict['event_data__location'],
                    'gps': gps,
                    'organizer': event_dict['event_data__organizer'],
                    'datetimes': {datetime_tuple},
                    'online': event_dict['event_data_gps__online'] == 1,
                    'geocoded_location': geocoded_location,
                    'keywords': {event_keyword} if event_keyword else set(),
                    'types': {event_type} if event_type else set()
                }
        return result_events

    def _find_duplicates(self, event_url: str, input_events: dict) -> list:
        input_tuples = []
        if event_url is not None:
            self._find_duplicate((1, 1, event_url, input_events))
        else:
            for index, event_url in enumerate(input_events):
                input_tuples.append((index + 1, len(input_events), event_url, input_events))

        with multiprocessing.Pool(32) as p:
            return p.map(DeduplicateEvents._find_duplicate, input_tuples)

    @staticmethod
    def _find_duplicate(input_tuple: tuple) -> dict:
        input_index, total_length, this_event_url, all_events = input_tuple

        this_event_dict = all_events[this_event_url]
        duplicate_output = ">>>\n {}\n".format(this_event_dict)
        debug_output = "{}/{} | De-duplicating URL: {}".format(input_index, total_length, this_event_url)
        count_same = 0
        duplicates = set()

        for other_event_url, other_event_dict in all_events.items():
            if this_event_dict['url'] == other_event_dict['url']:
                continue

            if DeduplicateEvents._are_short_texts_almost_equal(this_event_dict['title'], other_event_dict['title']) \
                    and DeduplicateEvents._are_long_texts_almost_equal(this_event_dict['perex'],
                                                                       other_event_dict['perex']) \
                    and DeduplicateEvents._are_short_texts_almost_equal(this_event_dict['location'],
                                                                        other_event_dict['location']) \
                    and DeduplicateEvents._are_short_texts_almost_equal(this_event_dict['geocoded_location'],
                                                                        other_event_dict['geocoded_location']) \
                    and DeduplicateEvents._are_gps_coords_almost_equal(this_event_dict['gps'], other_event_dict['gps']) \
                    and DeduplicateEvents._are_lists_almost_equal(this_event_dict['datetimes'],
                                                                  other_event_dict['datetimes']) \
                    and DeduplicateEvents._are_lists_almost_equal(this_event_dict['keywords'],
                                                                  other_event_dict['keywords']) \
                    and DeduplicateEvents._are_lists_almost_equal(this_event_dict['types'], other_event_dict['types']):
                count_same += 1
                duplicate_output += "==\n{}\n".format(other_event_dict)
                duplicates.add(other_event_dict['id'])

        debug_output += " | {}".format(count_same)
        # if count_same != 0:
        #     debug_output += "\n{}".format(duplicate_output)
        print(debug_output)

        return {
            'event_id': this_event_dict['id'],
            'duplicates': list(duplicates),
            'fetched_at': this_event_dict['downloaded_at']
        }

    @staticmethod
    def _are_short_texts_almost_equal(this_text: str, other_text: str) -> bool:
        this_text_dict, this_text_word_count = DeduplicateEvents._get_word_count_dict(this_text)
        other_text_dict, other_text_word_count = DeduplicateEvents._get_word_count_dict(other_text)

        max_word_count = max(this_text_word_count, other_text_word_count)
        same_words_count = DeduplicateEvents._get_same_keys_count(this_text_dict, other_text_dict)

        return (same_words_count / max_word_count) >= 0.8 if max_word_count != 0 else True

    @staticmethod
    def _get_word_count_dict(string: str) -> (dict, int):
        if string is None:
            return dict(), 0

        words_list = string.split()
        string_dict = defaultdict(int)
        string_word_count = 0

        for word in words_list:
            cancelled_match = DeduplicateEvents.CANCELLED_REGEX.match(word)
            deferred_match = DeduplicateEvents.DEFERRED_REGEX.match(word)
            word_match = DeduplicateEvents.IS_WORD_REGEX.match(word)
            if cancelled_match is not None or deferred_match is not None or word_match is None:
                continue
            string_dict[word] += 1
            string_word_count += 1

        return string_dict, string_word_count

    @staticmethod
    def _get_same_keys_count(this_dict: dict, other_dict: dict) -> int:
        same_keys_count = 0
        for this_word in this_dict:
            if this_word in other_dict:
                same_keys_count += min(this_dict[this_word], other_dict[this_word])
        return same_keys_count

    @staticmethod
    def _are_long_texts_almost_equal(this_text: str, other_text: str) -> bool:
        if this_text is None and other_text is None:
            return True
        if this_text is None or other_text is None:
            return False

        this_text = DeduplicateEvents._sanitize_text(this_text).split(" ")
        other_text = DeduplicateEvents._sanitize_text(other_text).split(" ")

        this_grams = defaultdict(int)
        other_grams = defaultdict(int)
        for i in range(len(this_text) - 4):
            this_grams[" ".join(this_text[i:i + 4])] += 1
            other_grams[" ".join(other_text[i:i + 4])] += 1

        max_grams_count = max(len(this_grams), len(other_grams))
        same_grams_count = DeduplicateEvents._get_same_keys_count(this_grams, other_grams)

        return (same_grams_count / max_grams_count) >= 0.8 if max_grams_count != 0 else True

    @staticmethod
    def _sanitize_text(text: str) -> str:
        text = DeduplicateEvents.SPECIAL_CHARACTER_REGEX.sub(" \\1 ", text)
        text = " ".join(text.split())
        return text

    @staticmethod
    def _are_lists_almost_equal(this_list: list, other_list: list) -> bool:
        common_elements_count = len(set(this_list) & set(other_list))
        all_unique_elements_count = len(set(this_list) | set(other_list))
        return (common_elements_count / float(all_unique_elements_count)) >= 0.8 \
            if all_unique_elements_count != 0 else True

    @staticmethod
    def _are_gps_coords_almost_equal(this_gps: str, other_gps: str) -> bool:
        if this_gps is None and other_gps is None:
            return True
        if this_gps is None or other_gps is None:
            return False

        this_latitude, this_longitude = map(lambda x: float(x), this_gps.split(','))
        other_latitude, other_longitude = map(lambda x: float(x), other_gps.split(','))

        earth_radius = 6371
        a = math.pow(math.sin(DeduplicateEvents.degrees_to_radians(other_latitude - this_latitude) / 2), 2) + \
            math.cos(DeduplicateEvents.degrees_to_radians(this_latitude)) * \
            math.cos(DeduplicateEvents.degrees_to_radians(other_latitude)) * \
            math.pow(math.sin(DeduplicateEvents.degrees_to_radians(other_longitude - this_longitude) / 2), 2)

        return (2 * earth_radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))) <= 5

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        return degrees * (math.pi / 180)

    def _update_database(self, duplicates_to_mark: list, dry_run: bool) -> None:
        if not dry_run:
            print("Updating DB...")

        sorted_duplicates = sorted(duplicates_to_mark, key=lambda x: x['fetched_at'], reverse=True)
        duplicates_count = 0
        marked_as_duplicates = set()
        output_dict = {}

        for duplicate_dict in sorted_duplicates:
            event_id = duplicate_dict['event_id']
            event_duplicates = duplicate_dict['duplicates']

            if event_id in marked_as_duplicates or len(event_duplicates) == 0:
                continue

            duplicates_count += len(event_duplicates)
            marked_as_duplicates.update(event_duplicates)
            output_dict[event_id] = event_duplicates

            query = '''
                        UPDATE event_url
                        SET duplicate_of = {}
                        WHERE id IN ({})
                    '''.format(event_id, ', '.join([str(duplicate_id) for duplicate_id in event_duplicates]))

            if not dry_run:
                try:
                    self.connection.execute(query)
                except sqlite3.Error as e:
                    print("Error occurred when updating 'duplicate_of' value in 'event_url' table: {}".format(str(e)))
        if not dry_run:
            self.connection.commit()

        print(">> Number of events{}marked as duplicates: {}".format("that would be" if dry_run else " ",
                                                                     duplicates_count))
        print(">> Events with its duplicates' event_url IDs: {}".format(output_dict))


if __name__ == '__main__':
    deduplicate_events = DeduplicateEvents()
    deduplicate_events.run()
