import json
import locale
import os
import re
from datetime import datetime

from lxml import etree


class Parser:
    PARSERS_DIR_PATH = "resources/parsers"
    ORDINATION = ["title", "perex", "datetime", "location", "gps", "organizer", "types"]
    DATE_TIME_DELIMITER = "%;"

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
        self.name = parser_name
        self.dom = None
        self.metadata = self._load_parser_file(parser_name)
        self.error_messages = []

    def set_dom(self, dom: etree.ElementTree) -> None:
        self.dom = dom

    def _load_parser_file(self, parser_name: str) -> dict:
        parser_file_path = os.path.join(self.PARSERS_DIR_PATH, parser_name + ".json")

        with open(parser_file_path) as parser_file:
            metadata = json.load(parser_file)

        return metadata

    def _get_roots(self, page: str) -> list:
        if page not in self.metadata:
            raise Exception("Page '{}' is not defined for '{}' parser!".format(page, self.name))

        if self.dom is None:
            raise Exception("You have to specify DOM to search (use function Parser.set_dom(etree.ElementTree))!")

        page_metadata = self.metadata[page]
        root_xpath_data = page_metadata["root"]["xpath"]
        root_selectors = root_xpath_data["selectors"]
        root_match = root_xpath_data["match"] if "match" in root_xpath_data else "ALL"

        root_elements = []
        for selector in root_selectors:
            found_elements = self.dom.xpath(selector)
            root_elements.extend(found_elements)

        if len(root_elements) == 0:
            error = "No root element of '{}' page found!".format(page)
            if error not in self.error_messages:
                self.error_messages.append(error)
        else:
            if root_match == "FIRST":
                root_elements = [root_elements[0]]

        return root_elements

    def get_event_urls(self) -> list:
        event_url_elements = self._get_xpath_results("calendar", "event_url")
        return event_url_elements

    def get_event_data(self) -> dict:
        parsed_event_data = {}

        event_data_keys = list(self.metadata["event"].keys())
        event_data_keys.remove("root")

        for key in event_data_keys:
            xpath_results = self._get_xpath_results("event", key)
            sanitized_xpath_results = self._sanitize_xpath_event_data(key, xpath_results)
            formatted_results = self._format_xpath_event_data(key, sanitized_xpath_results)
            sanitized_formatted_results = self._sanitize_xpath_event_data(key, formatted_results)
            regex_result = self._apply_regex(key, sanitized_formatted_results)

            parsed_event_data[key] = None
            if regex_result:
                parsed_event_data[key] = regex_result

        finalized_event_data = self._finalize_data(parsed_event_data)
        result_event_data = self._get_correct_counts(finalized_event_data)

        return result_event_data

    def _get_xpath_results(self, page: str, data_key: str) -> list:
        page_roots = self._get_roots(page)
        if len(page_roots) == 0:
            return []

        page_metadata = self.metadata[page]
        data_key_xpath_data = page_metadata[data_key]["xpath"]
        data_key_selectors = data_key_xpath_data["selectors"]

        data_key_elements = []
        for root in page_roots:
            for selector in data_key_selectors:
                try:
                    found_elements = root.xpath(selector)
                    data_key_elements.extend(found_elements)
                except etree.XPathEvalError:
                    pass

            # if len(data_key_elements) == 0:
            #     error = "No xpath matching values for '{}' where found!".format(data_key)
            #     if error not in self.error_messages:
            #         self.error_messages.append(error)

        return data_key_elements

    def _sanitize_xpath_event_data(self, data_key: str, xpath_values: list) -> list:
        if len(xpath_values) == 0:
            return []

        sanitized_values = [el.replace('\xa0', ' ') for el in xpath_values]
        sanitized_values = [el.strip() for el in sanitized_values]
        sanitized_values = filter(None, sanitized_values)

        values_to_ignore = self.metadata["event"][data_key]["xpath"].get("ignore", [])
        sanitized_values = filter(lambda x: x not in values_to_ignore, sanitized_values)

        seen = set()
        sanitized_values = [x for x in sanitized_values if not (x in seen or seen.add(x))]

        return list(sanitized_values)

    def _format_xpath_event_data(self, data_key: str, xpath_values: list) -> list:
        if len(xpath_values) == 0:
            return []

        xpath_event_data = self.metadata["event"][data_key]["xpath"]

        if "match" in xpath_event_data and xpath_event_data["match"] == "FIRST":
            xpath_values = [xpath_values[0]]

        if "join_separator" in xpath_event_data:
            separator = xpath_event_data["join_separator"]
            joined_value = separator.join(xpath_values)

            return [joined_value]

        elif "split_separator" in xpath_event_data:
            separator = xpath_event_data["split_separator"]
            split_result = []

            for value in xpath_values:
                split_value = value.split(separator)
                split_result.extend(split_value)

            return split_result

        return xpath_values

    def _apply_regex(self, data_key: str, xpath_values: list) -> list:
        if len(xpath_values) == 0:
            return []

        event_key_data = self.metadata["event"][data_key]

        if "regex" not in event_key_data:
            return xpath_values

        regex_data = event_key_data["regex"]
        expressions = regex_data["expressions"]
        groups = regex_data["group"] if "group" in regex_data else None
        match = regex_data["match"] if "match" in regex_data else "ALL"

        regexed_values = []
        for data in xpath_values:
            for expression in expressions:
                regex = re.compile(expression)
                matched_value = regex.search(str(data))
                if matched_value:
                    result = {}
                    if groups:
                        for group_num, group_name in groups.items():
                            result[group_name] = matched_value.group(int(group_num))
                            regexed_values.append(result)
                    else:
                        regexed_values.append(matched_value.group(0))

        if len(regexed_values) == 0:
            error = "No regex matching values for '{}' where found!".format(data_key)
            # if error not in self.error_messages:
            #     self.error_messages.append(error)
        else:
            if match == "FIRST":
                regexed_values = [regexed_values[0]]

        return regexed_values

    def _finalize_data(self, all_data: dict):
        if "date" in all_data:
            joined_datetime = None
            if all_data["date"]:
                joined_datetime = all_data["date"][0]
            del all_data["date"]

            if "time" in all_data:
                if all_data["time"]:
                    joined_datetime += "{}{}".format(self.DATE_TIME_DELIMITER, all_data["time"][0])
                del all_data["time"]

            all_data["datetime"] = [joined_datetime] if joined_datetime else None

        if "gps" in all_data and all_data["gps"]:
            result = []

            for data in all_data["gps"]:
                if "Lat" in data and "Lon" in data:
                    found_gps = "{},{}".format(str(data["Lat"]), str(data["Lon"]))
                    result.append(found_gps)

            all_data["gps"] = result

        all_data = dict([(key, all_data[key] if key in all_data else None) for key in self.ORDINATION])

        return all_data

    def _get_correct_counts(self, all_data: dict) -> dict:
        for data_key, result_values in all_data.items():
            if result_values is None:
                continue

            if data_key == "datetime" or data_key == "types":
                result = json.dumps(result_values, ensure_ascii=False)
                all_data[data_key] = result
            else:
                if len(result_values) > 1:
                    self.error_messages.append(
                        "Data key '{}' doesn't expect more than one result value!".format(data_key))
                all_data[data_key] = result_values[0]

        return all_data

    def process_datetimes(self, db_datetimes: list) -> list:
        formats = self._prepare_formats()
        parsed_datetimes = []

        locale.setlocale(locale.LC_TIME, "cs_CZ")
        for db_datetime in db_datetimes:
            db_datetime = self._replace_months(db_datetime)

            dt_delimiter_match = re.search(self.DATE_TIME_DELIMITER, db_datetime)
            if dt_delimiter_match:
                db_datetime = self._reorder_date_time(db_datetime)

            parsed_dt = self._process_datetime(db_datetime, formats)
            if parsed_dt:
                parsed_datetimes.append(parsed_dt)

        return parsed_datetimes

    def _prepare_formats(self) -> set:
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
                for time in time_metadata:
                    dt_format = self._reorder_date_time("{}{}{}".format(date, self.DATE_TIME_DELIMITER, time))
                    datetime_formats.add(dt_format)

        return datetime_formats

    def _reorder_date_time(self, datetime_str: str) -> str:
        date_str, _, time_str = datetime_str.partition(self.DATE_TIME_DELIMITER)
        date_range_match = re.search(self.RANGE_MATCH_REGEX, date_str)
        time_range_match = re.search(self.RANGE_MATCH_REGEX, time_str)

        result_datetime = ""

        if date_range_match:
            start_date = date_range_match.group(1).strip()
            delimiter = date_range_match.group(2)
            end_date = date_range_match.group(3).strip()

            if time_range_match:
                start_time = time_range_match.group(1).strip()
                end_time = time_range_match.group(3).strip()
                result_datetime = "{} {} %range{{{}}} {} {}".format(start_date, start_time, delimiter, end_date,
                                                                    end_time)
            else:
                result_datetime = "{} {} %range{{{}}} {}".format(start_date, time_str, delimiter, end_date)
        else:
            if time_range_match:
                time_str = re.sub(self.RANGE_MATCH_REGEX, '-', time_str)
            result_datetime += "{} {}".format(date_str, time_str)

        return result_datetime

    def _replace_months(self, datetime_str: str) -> str:
        for month, replacement in self.MONTHS_TO_REPLACE.items():
            datetime_str = re.sub(month, replacement, datetime_str)
        return datetime_str

    def _process_datetime(self, datetime_str: str, formats: set) -> tuple:
        start_date, start_time, end_date, end_time = None, None, None, None

        for dt_format in formats:
            range_match = re.search(self.RANGE_MATCH_REGEX, dt_format)

            if range_match:
                start_format = range_match.group(1).strip()
                delimiter = range_match.group(2)
                end_format = range_match.group(3).strip()

                start_str, _, end_str = datetime_str.partition(delimiter)

                try:
                    start_datetime = datetime.strptime(start_str.strip(), start_format)
                    start_date = self._get_date(start_datetime, start_format)
                    start_time = self._get_time(start_datetime, start_format)

                    end_datetime = datetime.strptime(end_str.strip(), end_format)
                    end_date = self._get_date(end_datetime, end_format)
                    end_time = self._get_time(end_datetime, end_format)
                except ValueError:
                    pass
            else:
                try:
                    start_datetime = datetime.strptime(datetime_str.strip(), dt_format.strip())
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
