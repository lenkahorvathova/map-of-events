import json
import os
import re
from typing import List, Union

from lxml import etree

from lib import logger


class Parser:
    """ OOP parser encapsulating the logic of data parsing from the specified DOM according to a specific template. """

    PARSERS_DIR_PATH = "resources/parsers"
    ORDINATION = ["title", "perex", "datetime", "location", "gps", "organizer", "types"]
    DATE_TIME_DELIMITER = "%;"
    COORDINATE_REGEX = re.compile(r'\\-?\d+.\d+')

    def __init__(self, parser_name: str) -> None:
        self.name = parser_name
        self.dom = None
        self.metadata = self.load_parser_file(parser_name)
        self.error_messages = []
        self.logger = logger.set_up_script_logger(__name__)

    def set_dom(self, dom: etree.ElementTree) -> None:
        self.dom = dom

    @staticmethod
    def load_parser_file(parser_name: str) -> dict:
        parser_file_path = os.path.join(Parser.PARSERS_DIR_PATH, parser_name + ".json")
        with open(parser_file_path) as parser_file:
            return json.load(parser_file)

    def _get_roots(self, page: str) -> List[etree._Element]:
        if page not in self.metadata:
            exception_msg = "Page '{}' is not defined for '{}' parser!".format(page, self.name)
            self.logger.critical(exception_msg)
            raise Exception(exception_msg)

        if self.dom is None:
            exception_msg = "You have to specify DOM to search (use function Parser.set_dom(etree.ElementTree))!"
            self.logger.critical(exception_msg)
            raise Exception(exception_msg)

        page_metadata = self.metadata[page]
        root_xpath_data = page_metadata["root"]["xpath"]
        root_elements = []
        for selector in root_xpath_data["selectors"]:
            found_elements = self.dom.xpath(selector)
            root_elements.extend(found_elements)

        if len(root_elements) == 0:
            error = "No root element of '{}' page found!".format(page)
            if error not in self.error_messages:
                self.error_messages.append(error)
        else:
            root_match = root_xpath_data["match"] if "match" in root_xpath_data else "ALL"
            if root_match == "FIRST":
                root_elements = [root_elements[0]]

        return root_elements

    def get_event_urls(self) -> List[str]:
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

    def _get_xpath_results(self, page: str, data_key: str) -> List[str]:
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
                    found_elements = self._remove_html_tags(found_elements)
                    data_key_elements.extend(found_elements)
                except etree.XPathEvalError:
                    pass
        return data_key_elements

    @staticmethod
    def _remove_html_tags(elements: List[Union[str, etree._Element]]) -> List[str]:
        result_elements = []
        for element in elements:
            if isinstance(element, etree._Element):
                inner_text = ''.join(element.itertext())
            else:
                inner_text = str(element)
            result_elements.append(inner_text)
        return result_elements

    def _sanitize_xpath_event_data(self, data_key: str, xpath_values: List[str]) -> List[str]:
        if len(xpath_values) == 0:
            return []

        sanitized_values = [el.replace('\xa0', ' ') for el in xpath_values]
        sanitized_values = [el.strip() for el in sanitized_values]
        sanitized_values = filter(None, sanitized_values)
        values_to_ignore = self.metadata["event"][data_key]["xpath"].get("ignore", [])
        sanitized_values = filter(lambda x: x not in values_to_ignore, sanitized_values)

        return list(sanitized_values)

    def _format_xpath_event_data(self, data_key: str, xpath_values: List[str]) -> List[str]:
        if len(xpath_values) == 0:
            error = "No xpath matching values for '{}' where found!".format(data_key)
            if error not in self.error_messages:
                self.error_messages.append(error)
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

    def _apply_regex(self, data_key: str, xpath_values: List[str]) -> List[str]:
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
            if error not in self.error_messages:
                self.error_messages.append(error)
        else:
            if match == "FIRST":
                regexed_values = [regexed_values[0]]
        return regexed_values

    @staticmethod
    def _finalize_data(all_data: dict) -> dict:
        if "date" in all_data:
            joined_datetime = None
            if all_data["date"]:
                joined_datetime = all_data["date"][0]
            del all_data["date"]

            if "time" in all_data:
                if all_data["time"]:
                    joined_datetime += "{}{}".format(Parser.DATE_TIME_DELIMITER, all_data["time"][0])
                del all_data["time"]

            all_data["datetime"] = [joined_datetime] if joined_datetime else None

        if "gps" in all_data and all_data["gps"]:
            result = []

            for data in all_data["gps"]:
                if isinstance(data, dict):
                    if "Lat" in data and "Lon" in data:
                        found_gps = "{},{}".format(str(data["Lat"]), str(data["Lon"]))
                        result.append(found_gps)
                elif isinstance(data, str):
                    split_data = data.split(',')
                    if len(split_data) == 2 and Parser.COORDINATE_REGEX.search(split_data[0]) \
                            and Parser.COORDINATE_REGEX.search(split_data[1]):
                        result.append(data)

            all_data["gps"] = result

        all_data = dict([(key, all_data[key] if key in all_data else None) for key in Parser.ORDINATION])

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
