import locale
import re
from datetime import datetime
from typing import Optional, List, Set

from lib.parser import Parser


class DatetimeParser:
    """ OOP parser encapsulating the logic of event's datetime parsing. """

    DEFAULT_DATETIME_FORMAT = "%d.%m.%Y %H:%M"
    DEFAULT_DATE_FORMAT = "%d.%m.%Y"
    DEFAULT_TIME_FORMAT = "%H:%M"

    RANGE_MATCH_REGEX = r'(.*)%range{(.*)}(.*)'
    CONTAINS_DATE_REGEX = r'%d|%b|%B|%m|%y|%Y|%x|%c'
    CONTAINS_TIME_REGEX = r'%H|%I|%p|%M|%S|%f|%X|%c'

    MONTHS_TO_REPLACE = {
        "leden": "ledna",
        "únor": "února",
        "březen": "března",
        "duben": "dubna",
        "květen": "května",
        "červen": "června",
        "červenec": "července",
        "srpen": "srpna",
        "září": "září",
        "říjen": "října",
        "listopad": "listopadu",
        "prosinec": "prosince"
    }

    def __init__(self, parser_name: str) -> None:
        self.metadata = Parser.load_parser_file(parser_name)
        self.error_messages = []

    def process_datetimes(self, db_datetimes: List[str]) -> List[tuple]:
        formats = self._prepare_formats()
        parsed_datetimes = []

        locale.setlocale(locale.LC_TIME, "cs_CZ")
        for db_datetime in db_datetimes:
            db_datetime = self._replace_months(db_datetime)
            db_datetime = self._replace_hyphen_to_dash(db_datetime)

            dt_delimiter_match = re.search(Parser.DATE_TIME_DELIMITER, db_datetime)
            if dt_delimiter_match:
                range_delimiter = self._get_range_delimiter_from_format(formats)
                db_datetime = self._reorder_date_time(db_datetime, range_delimiter)

            parsed_dt = self._process_datetime(db_datetime, formats)
            start_date, _, _, _ = parsed_dt
            if start_date:
                parsed_datetimes.append(parsed_dt)

        return parsed_datetimes

    def _prepare_formats(self) -> Set[str]:
        datetime_metadata = self.metadata["event"].get("datetime", None)
        datetime_formats = set()

        if datetime_metadata:
            datetime_formats.update(datetime_metadata.get("formats", []))
            datetime_formats.add(self.DEFAULT_DATETIME_FORMAT)
        else:
            date_metadata = self.metadata["event"].get("date", {}).get("formats", [])
            time_metadata = self.metadata["event"].get("time", {}).get("formats", [])

            date_metadata.append(self.DEFAULT_DATE_FORMAT)
            time_metadata.append(self.DEFAULT_TIME_FORMAT)

            for date in date_metadata:
                datetime_formats.add(date)
                for time in time_metadata:
                    datetime_formats.add(time)
                    dt_format = self._reorder_date_time("{}{}{}".format(date, Parser.DATE_TIME_DELIMITER, time))
                    datetime_formats.add(dt_format)

        datetime_formats.add(self.DEFAULT_DATE_FORMAT)
        return set([self._replace_hyphen_to_dash(self._remove_whitespaces(dt_format))
                    for dt_format in datetime_formats])

    def _reorder_date_time(self, datetime_str: str, range_delimiter: str = None) -> str:
        date_str, _, time_str = datetime_str.partition(Parser.DATE_TIME_DELIMITER)

        if range_delimiter:
            date_range_match = re.search(r'(.*)(' + range_delimiter + ')(.*)', date_str)
            time_range_match = re.search(r'(.*)(' + range_delimiter + ')(.*)', time_str)
        else:
            date_range_match = re.search(self.RANGE_MATCH_REGEX, date_str)
            time_range_match = re.search(self.RANGE_MATCH_REGEX, time_str)

        result_datetime = ""
        if date_range_match:
            start_date = date_range_match.group(1).strip()
            delimiter = date_range_match.group(2)
            end_date = date_range_match.group(3).strip()

            if not range_delimiter:
                delimiter = "%range{{{}}}".format(delimiter)

            if time_range_match:
                start_time = time_range_match.group(1).strip()
                end_time = time_range_match.group(3).strip()
                result_datetime = "{} {} {} {} {}".format(start_date, start_time, delimiter, end_date, end_time)
            else:
                result_datetime = "{} {} {} {}".format(start_date, time_str, delimiter, end_date)
        else:
            if time_range_match:
                time_str = re.sub(self.RANGE_MATCH_REGEX, '-', time_str)
            result_datetime += "{} {}".format(date_str, time_str)

        return result_datetime

    def _replace_months(self, datetime_str: str) -> str:
        for month, replacement in self.MONTHS_TO_REPLACE.items():
            datetime_str = re.sub(r"{}\b".format(month), replacement, datetime_str)
        return datetime_str

    def _get_range_delimiter_from_format(self, formats: Set[str]) -> Optional[str]:
        for dt_format in formats:
            range_match = re.search(self.RANGE_MATCH_REGEX, dt_format)
            if range_match:
                return range_match.group(2)
        return None

    def _process_datetime(self, datetime_str: str, formats: Set[str]) -> (datetime, datetime, datetime, datetime):
        start_date, start_time, end_date, end_time = None, None, None, None

        for dt_format in formats:
            range_match = re.search(self.RANGE_MATCH_REGEX, dt_format)

            if range_match:
                start_format = self._remove_whitespaces(range_match.group(1))
                delimiter = self._remove_whitespaces(range_match.group(2))
                end_format = self._remove_whitespaces(range_match.group(3))

                start_str, _, end_str = datetime_str.partition(delimiter)
                start_str = self._remove_whitespaces(start_str)
                end_str = self._remove_whitespaces(end_str)

                try:
                    start_datetime = datetime.strptime(start_str, start_format)
                    start_date = self._get_date(start_datetime, start_format)
                    start_time = self._get_time(start_datetime, start_format)

                    end_datetime = datetime.strptime(end_str, end_format)
                    end_date = self._get_date(end_datetime, end_format)
                    end_time = self._get_time(end_datetime, end_format)
                except ValueError:
                    pass
            else:
                datetime_str = self._remove_whitespaces(datetime_str)
                try:
                    start_datetime = datetime.strptime(datetime_str, dt_format)
                    start_date = self._get_date(start_datetime, dt_format)
                    start_time = self._get_time(start_datetime, dt_format)
                except ValueError:
                    pass

        return start_date, start_time, end_date, end_time

    def _get_date(self, input_datetime: datetime, used_format: str):
        date_match = re.search(self.CONTAINS_DATE_REGEX, used_format)
        return input_datetime.date().__str__() if date_match else None

    def _get_time(self, input_datetime: datetime, used_format: str):
        time_match = re.search(self.CONTAINS_TIME_REGEX, used_format)
        return input_datetime.time().__str__() if time_match else None

    @staticmethod
    def _remove_whitespaces(string: str) -> str:
        string = " ".join(string.split())
        string = ".".join([str_part.strip() for str_part in string.split(".")])
        delimiter_match = re.match(DatetimeParser.RANGE_MATCH_REGEX, string)
        if delimiter_match:
            delimiter = delimiter_match.group(2)
            string = delimiter.join([str_part.strip() for str_part in string.split(delimiter)])
            delimiter_macro = "%range{" + delimiter + "}"
            string = delimiter_macro.join([str_part.strip() for str_part in string.split(delimiter_macro)])
        return string

    @staticmethod
    def _replace_hyphen_to_dash(string: str) -> str:
        return string.replace('–', '-')
