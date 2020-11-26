from datetime import date, timedelta, datetime
from typing import List

from lib import utils


class GetAverageFutureCount:
    """ Computes a daily average count of events that are in the future. """

    def __init__(self) -> None:
        self.connection = utils.create_connection()
        utils.check_db_views(self.connection, ["event_data_view_valid_events_only"])

    def run(self) -> None:
        start_date, end_date = self._get_dates()
        day_counts = self._get_days_counts(start_date, end_date)
        self._count_average(day_counts)

    def _get_dates(self) -> (date, date):
        print("Getting days range...")
        query = '''
                    SELECT strftime('%Y-%m-%d', min(calendar__downloaded_at)), 
                           strftime('%Y-%m-%d', max(calendar__downloaded_at))
                    FROM event_data_view_valid_events_only
                '''
        cursor = self.connection.execute(query)
        start, end = cursor.fetchone()
        return datetime.strptime(start, '%Y-%m-%d').date(), datetime.strptime(end, '%Y-%m-%d').date()

    def _get_days_counts(self, start: date, end: date) -> dict:
        print("Counting future events for each day...")
        result = {}
        for day in self._datetime_range(start, end):
            result[date.strftime(day, '%Y-%m-%d')] = self._get_future_count(day)
        return result

    @staticmethod
    def _datetime_range(start: date, end: date) -> List[date]:
        delta = end - start
        for i in range(delta.days + 1):
            yield start + timedelta(days=i)

    def _get_future_count(self, day: date) -> int:
        query = '''
                    SELECT count(DISTINCT event_data__id) AS future_events_count
                    FROM event_data_view_valid_events_only
                    WHERE calendar__downloaded_at <= date('{}')
                      AND (event_data_datetime__start_date >= date('{}')
                       OR (event_data_datetime__end_date IS NOT NULL AND event_data_datetime__end_date >= date('{}')));
                '''.format(day, day, day)
        cursor = self.connection.execute(query)
        return cursor.fetchone()[0]

    @staticmethod
    def _count_average(day_counts: dict) -> None:
        average = sum(day_counts.values()) / len(day_counts.keys())
        print(">> On average there are {} events in the future.".format(round(average)))


if __name__ == '__main__':
    get_average_future_count = GetAverageFutureCount()
    get_average_future_count.run()
