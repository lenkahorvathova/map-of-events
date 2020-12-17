import argparse
import os
import sqlite3
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser


class DeleteHtmlFiles:
    """ Deletes HTML files related to calendars downloaded more than the specified days ago. """

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, log_level=self.args.log_level)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_views(self.connection, ['event_data_view'])
            utils.check_db_tables(self.connection, ['calendar', 'event_html'])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Deletes HTML files related to calendars downloaded more than the specified days ago.")
        parser.add_argument('days_ago', type=int, help="delete HTML files older than the specified days ago")
        return parser.parse_args()

    def run(self) -> None:
        all_file_paths, calendar_ids, event_html_ids = self._load_input_paths()
        self._delete_files(all_file_paths)
        self._update_database(calendar_ids, event_html_ids)

    def _load_input_paths(self) -> (List[str], List[int], List[int]):
        self.logger.info("Loading input file paths...")

        query = '''
                    SELECT calendar__id, calendar__html_file_path, 
                           event_html__id, event_html__html_file_path
                    FROM event_data_view
                    WHERE calendar__downloaded_at < date('now', '-{} days')
                '''.format(self.args.days_ago)
        cursor = self.connection.execute(query)

        all_file_paths = set()
        calendar_ids = set()
        event_html_ids = set()
        for calendar_id, calendar_file_path, event_html_id, event_html_file_path in cursor.fetchall():
            if calendar_file_path is not None:
                all_file_paths.add(calendar_file_path)
                calendar_ids.add(calendar_id)
            if event_html_file_path is not None:
                all_file_paths.add(event_html_file_path)
                event_html_ids.add(event_html_id)

        self.logger.info(">> Timestamp older than: {} days ago".format(self.args.days_ago))
        return list(sorted(all_file_paths)), list(sorted(calendar_ids)), list(sorted(event_html_ids))

    def _delete_files(self, all_file_paths: List[str]) -> None:
        if not self.args.dry_run:
            self.logger.info("Deleting HTML files...")

            for file_path in all_file_paths:
                if os.path.isfile(file_path):
                    os.remove(file_path)

        debug_msg = ">> {} files count: {}".format("Would-be-deleted" if self.args.dry_run else "Deleted",
                                                   len(all_file_paths))
        if len(all_file_paths) == 0:
            self.logger.warning(debug_msg)
        else:
            self.logger.info(debug_msg)
        if len(all_file_paths) > 0:
            self.logger.info('\n'.join(["List of the files:"] + all_file_paths))

    def _update_database(self, calendar_ids: List[int], event_html_ids: List[int]) -> None:
        if self.args.dry_run:
            return

        self.logger.info("Updating DB...")

        query = '''
                    UPDATE calendar
                    SET is_deleted = 1
                    WHERE id IN ({})
                '''.format(', '.join([str(c_id) for c_id in calendar_ids]))
        try:
            self.connection.execute(query)
        except sqlite3.Error as e:
            self.logger.error("Error occurred when updating 'is_deleted' in 'calendar' table: {}".format(str(e)))

        query = '''
                    UPDATE event_html
                    SET is_deleted = 1
                    WHERE id IN ({})
                '''.format(', '.join([str(eh_id) for eh_id in event_html_ids]))
        try:
            self.connection.execute(query)
        except sqlite3.Error as e:
            self.logger.error("Error occurred when updating 'is_deleted' in 'event_html' table: {}".format(str(e)))

        self.connection.commit()


if __name__ == '__main__':
    delete_html_files = DeleteHtmlFiles()
    delete_html_files.run()
