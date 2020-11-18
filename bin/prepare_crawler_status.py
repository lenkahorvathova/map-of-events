import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser


class PrepareCrawlerStatus:
    """ Prepares statistics for a crawler's status. """

    OUTPUT_FILE_PATH = "data/tmp/crawler_status_info.json"
    EMAIL_TEMPLATE_FILE_PATH = "resources/email/success_template.txt"
    EMAIL_RESULT_FILE_PATH = "data/tmp/email.txt"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, debug=self.args.debug)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection, ["calendar"])
            utils.check_db_views(self.connection, ["event_data_view"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Prepares statistics for a crawler's status.")
        return parser.parse_args()

    def run(self):
        self.logger.info('Preparing Crawler Status...')

        crawler_status_dict = self._prepare_crawler_status_dict()
        if self.args.dry_run:
            print(json.dumps(crawler_status_dict, indent=4, ensure_ascii=False))
        else:
            utils.store_to_json_file(crawler_status_dict, PrepareCrawlerStatus.OUTPUT_FILE_PATH)
        self._generate_email(crawler_status_dict['statistics']['count_per_week'][1])

        self.logger.info("DONE")

    def _prepare_crawler_status_dict(self) -> dict:
        crawler_status = {
            'statistics': {
                'total_count': self._get_total_events_count(),
                'future_count': self._get_future_events_count(),
                'count_per_day': self._get_events_count_per_day(14),
                'count_per_week': self._get_events_count_per_week(52),
                'count_per_calendar': self._get_events_count_per_calendar(),
                'count_per_parser': []
            },
            'failures': {
                'failed_calendars': self._get_failed_calendars(3),
                'empty_calendars': self._get_empty_calendars(),
                'failed_events_errors': self._get_failed_events_errors(7),
                'failure_percentage_per_calendar': []
            },
            'events': {},
            'calendars': {}
        }

        count_per_calendar = crawler_status['statistics']['count_per_calendar']
        crawler_status['statistics']['count_per_parser'] = self._get_events_count_per_parser(count_per_calendar)
        crawler_status['failures']['failure_percentage_per_calendar'] = self._get_failure_percentage_per_calendar(
            count_per_calendar, 10)

        crawler_status['events'] = self._get_related_events_info(crawler_status['failures']['failed_events_errors'])
        crawler_status['calendars'] = self._get_related_calendars_info()

        return crawler_status

    def _get_total_events_count(self) -> int:
        query = '''
                    SELECT count(DISTINCT event_data__id)
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                '''
        cursor = self.connection.execute(query)
        return cursor.fetchone()[0]

    def _get_future_events_count(self) -> int:
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

    def _get_events_count_per_day(self, last_n: int) -> List[dict]:
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
        db_result = {tpl[0]: tpl[1] for tpl in cursor.fetchall()}

        curr_date = datetime.now()
        for i in range(last_n):
            date_string = curr_date.strftime("%Y/%m/%d")
            if date_string not in db_result:
                db_result[date_string] = 0
            curr_date = curr_date - timedelta(days=1)

        result_dict = list(sorted([{
            'day': key,
            'count': value
        } for key, value in db_result.items()], key=lambda item: item['day'], reverse=True))

        return result_dict[:last_n]

    def _get_events_count_per_week(self, last_n: int) -> List[dict]:
        query = '''
                    SELECT strftime('%Y/%m/%d', calendar__downloaded_at) AS day, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                      AND event_url__duplicate_of IS NULL
                    GROUP BY day
                    ORDER BY day DESC
                    LIMIT {}
                '''.format(last_n * 7)
        cursor = self.connection.execute(query)
        counts_per_day = cursor.fetchall()

        tmp_dict = defaultdict(int)
        for day, count in counts_per_day:
            curr_date = datetime.strptime(day, '%Y/%m/%d')
            curr_year, curr_week, _ = curr_date.isocalendar()
            week_string = "{}-{}".format(str(curr_year), '0' + str(curr_week) if curr_week < 10 else str(curr_week))
            tmp_dict[week_string] += count

        curr_date = datetime.now()
        for i in range(last_n):
            curr_year, curr_week, _ = curr_date.isocalendar()
            week_string = "{}-{}".format(str(curr_year), '0' + str(curr_week) if curr_week < 10 else str(curr_week))
            if week_string not in tmp_dict:
                tmp_dict[week_string] = 0
            curr_date = curr_date - timedelta(days=7)

        result_dict = list(sorted([{
            'week': key,
            'count': value
        } for key, value in tmp_dict.items()], key=lambda item: item['week'], reverse=True))
        return result_dict[:last_n]

    def _get_events_count_per_calendar(self) -> dict:
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

    def _get_events_count_per_parser(self, events_per_calendar: dict) -> dict:
        events_per_parser_dict = {}

        for calendar_url, events_count in events_per_calendar.items():
            calendar_base = utils.get_base_by_url(calendar_url)
            calendar_parser = calendar_base['parser']
            if calendar_parser in events_per_parser_dict:
                events_per_parser_dict[calendar_parser] += events_count
            else:
                events_per_parser_dict[calendar_parser] = events_count

        return events_per_parser_dict

    def _get_failed_calendars(self, consecutive_last_n: int) -> List[dict]:
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

    def _get_empty_calendars(self) -> list:
        last_2_weeks_empty_calendars = self._get_empty_calendars_helper(14)
        always_empty_calendars = self._get_empty_calendars_helper(None)

        always_empty_calendars_list = [calendar['calendar_url'] for calendar in always_empty_calendars]
        for calendar_dict in last_2_weeks_empty_calendars:
            calendar_dict['always'] = calendar_dict['calendar_url'] in always_empty_calendars_list

        return last_2_weeks_empty_calendars

    def _get_empty_calendars_helper(self, consecutive_last_n: Optional[int]) -> List[dict]:
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

    def _get_failed_events_errors(self, last_n: int) -> List[dict]:
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
        failed_events = list(map(dict, set(tuple(sorted(event_dict.items())) for event_dict in failed_events)))

        return failed_events

    def _get_failure_percentage_per_calendar(self, parsed_events_per_calendar: dict,
                                             failure_threshold: int) -> List[dict]:
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

    def _get_related_events_info(self, list_with_event_url_ids: List[dict]) -> dict:
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
    def _get_related_calendars_info() -> dict:
        base_dict = utils.get_base_dict_per_url()

        return base_dict

    @staticmethod
    def _generate_email(last_week_dict: dict) -> None:
        with open(PrepareCrawlerStatus.EMAIL_TEMPLATE_FILE_PATH, 'r') as email_template:
            email = email_template.read()
        email = email.replace('%LAST_WEEK_NUMBER%', str(last_week_dict['week']))
        email = email.replace('%LAST_WEEK_EVENTS_COUNT%', str(last_week_dict['count']))
        with open(PrepareCrawlerStatus.EMAIL_RESULT_FILE_PATH, 'w') as email_result:
            email_result.write(email)


if __name__ == '__main__':
    prepare_crawler_status = PrepareCrawlerStatus()
    prepare_crawler_status.run()
