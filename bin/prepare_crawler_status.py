import argparse
import json
from typing import Optional

from lib import utils


class PrepareCrawlerStatus:
    OUTPUT_FILE_PATH = "data/tmp/crawler_status_info.json"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        missing_tables = utils.check_db_tables(self.connection, ["calendar"])
        if len(missing_tables) != 0:
            raise Exception("Missing tables in the DB: {}".format(missing_tables))
        missing_views = utils.check_db_views(self.connection, ["event_data_view"])
        if len(missing_views) != 0:
            raise Exception("Missing views in the DB: {}".format(missing_views))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")

        return parser.parse_args()

    def run(self):
        print('Preparing Crawler Status...', end="")
        crawler_status_dict = self.prepare_crawler_status_dict()
        if self.args.dry_run:
            print(json.dumps(crawler_status_dict, indent=4, ensure_ascii=False))
        else:
            utils.store_to_json_file(crawler_status_dict, PrepareCrawlerStatus.OUTPUT_FILE_PATH)
        print("DONE")

    def prepare_crawler_status_dict(self) -> dict:
        crawler_status = {
            'statistics': {
                'total_count': self.get_total_events_count(),
                'future_count': self.get_future_events_count(),
                'count_per_day': self.get_events_count_per_day(14),
                'count_per_week': self.get_events_count_per_week(53),
                'count_per_calendar': self.get_events_count_per_calendar(),
                'count_per_parser': []
            },
            'failures': {
                'failed_calendars': self.get_failed_calendars(3),
                'empty_calendars': self.get_empty_calendars(),
                'failed_events_errors': self.get_failed_events_errors(7),
                'failure_percentage_per_calendar': []
            },
            'events': {},
            'calendars': {}
        }

        count_per_calendar = crawler_status['statistics']['count_per_calendar']
        crawler_status['statistics']['count_per_parser'] = self.get_events_count_per_parser(count_per_calendar)
        crawler_status['failures']['failure_percentage_per_calendar'] = self.get_failure_percentage_per_calendar(
            count_per_calendar, 10)

        crawler_status['events'] = self.get_related_events_info(crawler_status['failures']['failed_events_errors'])
        crawler_status['calendars'] = self.get_related_calendars_info()

        return crawler_status

    def get_total_events_count(self) -> int:
        query = '''
                    SELECT count(DISTINCT event_data__id)
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                '''
        cursor = self.connection.execute(query)
        return cursor.fetchone()[0]

    def get_future_events_count(self) -> int:
        query = '''
                    SELECT count(DISTINCT event_data__id)
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data_datetime__start_date >= date('now') OR (event_data_datetime__end_date IS NOT NULL AND event_data_datetime__end_date >= date('now')))
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                '''
        cursor = self.connection.execute(query)
        return cursor.fetchone()[0]

    def get_events_count_per_day(self, last_n: int) -> list:
        query = '''
                    SELECT strftime('%Y/%m/%d', calendar__downloaded_at) AS day, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                    GROUP BY day
                    ORDER BY day DESC
                    LIMIT {}
                '''.format(last_n)
        cursor = self.connection.execute(query)
        return [{
            'day': tpl[0],
            'count': tpl[1]
        } for tpl in cursor.fetchall()]

    def get_events_count_per_week(self, last_n: int) -> list:
        query = '''
                    SELECT strftime('%Y-%W', calendar__downloaded_at) AS week, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                    GROUP BY week
                    ORDER BY week DESC
                    LIMIT {}
                '''.format(last_n)
        cursor = self.connection.execute(query)
        return [{
            'week': tpl[0],
            'count': tpl[1]
        } for tpl in cursor.fetchall()]

    def get_events_count_per_calendar(self) -> dict:
        query = '''
                    SELECT calendar__url AS calendar, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                    GROUP BY calendar
                '''
        cursor = self.connection.execute(query)

        result_dict = {}
        for tpl in cursor.fetchall():
            result_dict[tpl[0]] = tpl[1]
        return result_dict

    def get_events_count_per_parser(self, events_per_calendar: dict) -> dict:
        events_per_parser_dict = {}

        for calendar_url, events_count in events_per_calendar.items():
            calendar_base = utils.get_base_by_url(calendar_url)
            calendar_parser = calendar_base['parser']
            if calendar_parser in events_per_parser_dict:
                events_per_parser_dict[calendar_parser] += events_count
            else:
                events_per_parser_dict[calendar_parser] = events_count

        return events_per_parser_dict

    def get_failed_calendars(self, consecutive_last_n: int) -> list:
        query = '''
                    SELECT DISTINCT calendar.url
                    FROM calendar
                    WHERE date(calendar.downloaded_at) > date('now','-{} day')
                '''.format(consecutive_last_n)
        cursor = self.connection.execute(query)

        downloaded_calendars = [calendar[0] for calendar in cursor.fetchall()]
        base_calendars = [base['url'] for base in utils.get_active_base()]

        return [{
            'calendar_url': calendar
        } for calendar in base_calendars if calendar not in downloaded_calendars]

    def get_empty_calendars(self) -> list:
        last_2_weeks_empty_calendars = self.get_empty_calendars_helper(14)
        always_empty_calendars = self.get_empty_calendars_helper(None)

        always_empty_calendars_list = [calendar['calendar_url'] for calendar in always_empty_calendars]
        for calendar_dict in last_2_weeks_empty_calendars:
            calendar_dict['always'] = calendar_dict['calendar_url'] in always_empty_calendars_list

        return last_2_weeks_empty_calendars

    def get_empty_calendars_helper(self, consecutive_last_n: Optional[int]) -> list:
        query_last_n = ""
        if consecutive_last_n is not None:
            query_last_n = '''WHERE download_date > date('now', '-{} day')'''.format(consecutive_last_n)
        query = '''
                    SELECT DISTINCT calendar_url
                    FROM (
                             SELECT calendar_url, sum(events_count) AS events_sum
                             FROM (
                                      SELECT date(c.downloaded_at)  AS download_date,
                                             c.url                  AS calendar_url,                 
                                             c.all_event_url_count  AS events_count
                                      FROM calendar c
                                      {}
                                      GROUP BY download_date, calendar_url
                                  )
                             GROUP BY calendar_url
                         )
                    WHERE events_sum == 0;
                '''.format(query_last_n)
        cursor = self.connection.execute(query)

        base_dict = utils.get_base_dict_per_url()

        return [{
            'calendar_url': calendar[0],
            'parser': base_dict[calendar[0]]['parser']
        } for calendar in cursor.fetchall()]

    def get_failed_events_errors(self, last_n: int) -> list:
        failed_events_dict = {}

        query = '''
                    SELECT event_url__id, event_url__url, calendar__downloaded_at
                    FROM event_data_view
                    WHERE event_url__url IS NOT NULL
                      AND date(calendar__downloaded_at)  > date('now', '-{} day')
                      AND event_html__html_file_path IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_html_not_downloaded'] = cursor.fetchall()

        query = '''
                    SELECT event_url__id, event_url__url, calendar__downloaded_at
                    FROM event_data_view
                    WHERE date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_data_not_parsed'] = cursor.fetchall()

        query = '''
                    SELECT event_url__id, event_url__url, calendar__downloaded_at
                    FROM event_data_view
                    WHERE  date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NOT NULL
                      AND event_data_datetime__start_date IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_datetime_not_processed'] = cursor.fetchall()

        query = '''
                    SELECT event_url__id, event_url__url, calendar__downloaded_at
                    FROM event_data_view
                    WHERE  date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NOT NULL
                      AND event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NULL AND event_data_gps__gps IS NULL AND event_data_gps__online == 0)
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_gps_not_acquired'] = cursor.fetchall()

        failed_events = []
        for error, event_list in failed_events_dict.items():
            for event_url_id, event_url, downloaded_at in event_list:
                failed_events.append({
                    'event_url': event_url,
                    'event_url_id': event_url_id,
                    'downloaded_at': downloaded_at,
                    'error': error
                })

        return failed_events

    def get_failure_percentage_per_calendar(self, parsed_events_per_calendar: dict, failure_threshold: int) -> list:
        query = '''
                    SELECT calendar__url, count(DISTINCT event_url__url) AS events_count
                    FROM event_data_view
                    GROUP BY calendar__url
                '''
        cursor = self.connection.execute(query)
        all_events_per_calendar = cursor.fetchall()
        all_events_per_calendar_dict = dict(all_events_per_calendar)

        calendars_over_failure_treshold = []
        for calendar, events_count in parsed_events_per_calendar.items():
            all_events_count = all_events_per_calendar_dict[calendar]
            failed_events_count = all_events_count - events_count
            failure_percentage = (failed_events_count / all_events_count) * 100

            if failure_percentage >= failure_threshold:
                calendars_over_failure_treshold.append({
                    'calendar_url': calendar,
                    'events_failure': {
                        'all_events_count': all_events_count,
                        'failed_events_count': failed_events_count,
                        'failure_percentage': failure_percentage
                    }
                })

        return calendars_over_failure_treshold

    def get_related_events_info(self, list_with_event_url_ids: list) -> dict:
        events_url_ids = []
        for event_dict in list_with_event_url_ids:
            event_url_id = event_dict['event_url_id']
            events_url_ids.append(event_url_id)

        query = '''
                SELECT event_url__id, event_url__url,
                       event_html__html_file_path,
                       event_data__id, event_data__title, event_data__perex, event_data__datetime, event_data__location, event_data__gps, event_data__organizer, event_data__types
                FROM event_data_view
                WHERE event_url__id IN ({})
                '''.format(",".join([str(url) for url in events_url_ids]))
        cursor = self.connection.execute(query)
        events_info_tuples = cursor.fetchall()

        events_dict = {}
        for event_tuple in events_info_tuples:
            event_url = event_tuple[1]
            events_dict[event_url] = {
                'event_url__id': event_tuple[0],
                'event_url__url': event_tuple[1],
                'event_html__html_file_path': event_tuple[2],
                'event_data__id': event_tuple[3],
                'event_data__title': utils.sanitize_string_for_html(event_tuple[4]),
                'event_data__perex': utils.sanitize_string_for_html(event_tuple[5]),
                'event_data__datetime': json.loads(event_tuple[6]) if event_tuple[6] else [],
                'event_data__location': utils.sanitize_string_for_html(event_tuple[7]),
                'event_data__gps': event_tuple[8],
                'event_data__organizer': utils.sanitize_string_for_html(event_tuple[9]),
                'event_data__types': json.loads(event_tuple[10]) if event_tuple[10] else []
            }

        return events_dict

    @staticmethod
    def get_related_calendars_info() -> dict:
        base_dict = utils.get_base_dict_per_url()

        return base_dict


if __name__ == '__main__':
    prepare_crawler_status = PrepareCrawlerStatus()
    prepare_crawler_status.run()
