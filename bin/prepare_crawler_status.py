import json
from typing import Optional

from lib import utils


class PrepareCrawlerStatus:
    def __init__(self):
        self.connection = utils.create_connection()

        missing_tables = utils.check_db_tables(self.connection, ["calendar", "event_url", "event_html"])
        if len(missing_tables) != 0:
            raise Exception("Missing tables in the DB: {}".format(missing_tables))
        missing_views = utils.check_db_views(self.connection, ["event_data_view"])
        if len(missing_views) != 0:
            raise Exception("Missing views in the DB: {}".format(missing_views))

    def run(self):
        crawler_status = {
            'statistics': {
                'total_count': self.get_total_events_count(),
                'future_count': self.get_future_events_count(),
                'count_per_week': self.get_events_count_per_week(53),
                'count_per_day': self.get_events_count_per_day(14),
                'count_per_calendar': self.get_events_count_per_calendar()
            },
            'failures': {
                'failed_calendars': self.get_failed_calendars(3),
                'always_empty_calendars': self.get_empty_calendars(None),
                'newly_empty_calendars': self.get_empty_calendars(7),
                'failed_events_errors': self.get_failed_events_errors(7)
            }
        }

        count_per_calendar = crawler_status['statistics']['count_per_calendar']
        crawler_status['statistics']['count_per_parser'] = self.get_events_count_per_parser(count_per_calendar)
        crawler_status['failures']['failure_percentage_per_calendar'] = self.get_failure_percentage_per_calendar(
            count_per_calendar, 10)

        print(json.dumps(crawler_status, indent=4))

    def get_total_events_count(self) -> int:
        query = '''
                    SELECT count(DISTINCT event_data__id)
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
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
                '''
        cursor = self.connection.execute(query)
        return cursor.fetchone()[0]

    def get_events_count_per_week(self, last_n: int) -> list:
        query = '''
                    SELECT strftime('%Y-%W', calendar__downloaded_at) AS week, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                    GROUP BY week
                    ORDER BY week DESC
                    LIMIT {}
                '''.format(last_n)
        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def get_events_count_per_day(self, last_n: int) -> list:
        query = '''
                    SELECT strftime('%Y/%m/%d', calendar__downloaded_at) AS day, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                    GROUP BY day
                    ORDER BY day DESC
                    LIMIT {}
                '''.format(last_n)
        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def get_events_count_per_calendar(self) -> list:
        query = '''
                    SELECT calendar__url AS domain, count(DISTINCT event_data__id) AS events_count
                    FROM event_data_view
                    WHERE event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NOT NULL OR (event_data_gps__gps IS NOT NULL OR event_data_gps__online == 1))
                    GROUP BY domain
                '''
        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def get_events_count_per_parser(self, events_per_calendar: list) -> list:
        events_per_parser_dict = {}

        for calendar_url, events_count in events_per_calendar:
            calendar_base = utils.get_base_by_url(calendar_url)
            calendar_parser = calendar_base['parser']
            if calendar_parser in events_per_parser_dict:
                events_per_parser_dict[calendar_parser] += events_count
            else:
                events_per_parser_dict[calendar_parser] = events_count

        return list(events_per_parser_dict.items())

    def get_failed_calendars(self, consecutive_last_n: int) -> list:
        query = '''
                    SELECT DISTINCT calendar.url
                    FROM calendar
                    WHERE date(calendar.downloaded_at) > date('now','-{} day')
                '''.format(consecutive_last_n)
        cursor = self.connection.execute(query)

        downloaded_calendars = [calendar[0] for calendar in cursor.fetchall()]
        base_calendars = [base['url'] for base in utils.load_base()]

        return [calendar for calendar in base_calendars if calendar not in downloaded_calendars]

    def get_empty_calendars(self, consecutive_last_n: Optional[int]) -> list:
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
                                             count(DISTINCT eu.url) AS events_count
                                      FROM calendar c
                                           LEFT OUTER JOIN event_url eu ON c.id = eu.calendar_id
                                      {}
                                      GROUP BY download_date, calendar_url
                                  )
                             GROUP BY calendar_url
                         )
                    WHERE events_sum == 0;
                '''.format(query_last_n)
        cursor = self.connection.execute(query)

        return [calendar[0] for calendar in cursor.fetchall()]

    def get_failed_events_errors(self, last_n: int) -> list:
        failed_events_dict = {}

        query = '''
                    SELECT eu.url
                    FROM event_url eu
                        LEFT OUTER JOIN event_html eh ON eu.id = eh.event_url_id
                    WHERE date(eu.parsed_at) > date('now','-{} day')
                      AND eh.html_file_path IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_html_not_downloaded'] = [event_url[0] for event_url in cursor.fetchall()]

        query = '''
                    SELECT event_url__url
                    FROM event_data_view
                    WHERE date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_data_not_parsed'] = [event_url[0] for event_url in cursor.fetchall()]

        query = '''
                    SELECT event_url__url
                    FROM event_data_view
                    WHERE  date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NOT NULL
                      AND event_data_datetime__start_date IS NULL
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_datetime_not_processed'] = [event_url[0] for event_url in cursor.fetchall()]

        query = '''
                    SELECT event_url__url
                    FROM event_data_view
                    WHERE  date(calendar__downloaded_at) > date('now','-{} day')
                      AND event_html__html_file_path IS NOT NULL
                      AND event_data__id IS NOT NULL
                      AND event_data_datetime__start_date IS NOT NULL
                      AND (event_data__gps IS NULL AND event_data_gps__gps IS NULL AND event_data_gps__online == 0)
                '''.format(last_n)
        cursor = self.connection.execute(query)
        failed_events_dict['event_gps_not_acquired'] = [event_url[0] for event_url in cursor.fetchall()]

        failed_events = []
        for error, event_url_list in failed_events_dict.items():
            for event_url in event_url_list:
                failed_events.append((event_url, error))

        return failed_events

    def get_failure_percentage_per_calendar(self, events_per_calendar: list, failure_threshold: int) -> list:
        query = '''
                    SELECT calendar__url, count(DISTINCT event_url__url) AS events_count
                    FROM event_data_view
                    GROUP BY calendar__url
                '''
        cursor = self.connection.execute(query)
        all_events_per_calendar = cursor.fetchall()
        all_events_per_calendar_dict = dict(all_events_per_calendar)

        calendars_over_failure_treshold = []
        for calendar, events_count in events_per_calendar:
            all_events_count = all_events_per_calendar_dict[calendar]
            failed_events_count = all_events_count - events_count
            failure_percentage = (failed_events_count / all_events_count) * 100

            if failure_percentage >= failure_threshold:
                calendars_over_failure_treshold.append((calendar, failure_percentage))

        return calendars_over_failure_treshold


if __name__ == '__main__':
    prepare_crawler_status = PrepareCrawlerStatus()
    prepare_crawler_status.run()
