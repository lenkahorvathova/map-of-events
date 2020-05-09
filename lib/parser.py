import json
import os
import re

from lxml import etree


class Parser:
    PARSERS_DIR_PATH = "resources/parsers"

    def __init__(self, parser_name: str, dom: etree.ElementTree) -> None:
        self.name = parser_name
        self.dom = dom
        self.metadata = self._load_parser_file(parser_name)
        self.error_messages = []

    def _load_parser_file(self, parser_name: str) -> dict:
        parser_file_path = os.path.join(self.PARSERS_DIR_PATH, parser_name + ".json")

        with open(parser_file_path) as parser_file:
            metadata = json.load(parser_file)

        return metadata

    def _get_roots(self, page: str) -> list:
        if page not in self.metadata:
            raise Exception("Page '{}' is not defined for '{}' parser.".format(page, self.name))

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
        event_url_elements = self._get_xpath_results("calendar", "event_url", "No events where found!")
        return event_url_elements

    def get_event_data(self) -> dict:
        parsed_event_data = {}

        event_data_keys = list(self.metadata["event"].keys())
        event_data_keys.remove("root")

        for key in event_data_keys:
            xpath_results = self._get_xpath_results("event", key)
            sanitized_results = self._sanitize_xpath_event_data(key, xpath_results)
            formatted_results = self._format_xpath_event_data(key, sanitized_results)
            sanitized_results = self._sanitize_xpath_event_data(key, formatted_results)
            regex_result = self._apply_regex(key, sanitized_results)

            parsed_event_data[key] = None
            if regex_result:
                finalized_result = self._get_correct_counts(key, regex_result)
                parsed_event_data[key] = finalized_result

        return parsed_event_data

    def _get_xpath_results(self, page: str, data_key: str, error_message: str = None) -> list:
        page_roots = self._get_roots(page)
        if len(page_roots) == 0:
            return []

        page_metadata = self.metadata[page]
        data_key_xpath_data = page_metadata[data_key]["xpath"]
        data_key_selectors = data_key_xpath_data["selectors"]
        data_key_match = data_key_xpath_data["match"] if "match" in data_key_xpath_data else "ALL"

        data_key_elements = []
        for root in page_roots:
            for selector in data_key_selectors:
                try:
                    found_elements = root.xpath(selector)
                    data_key_elements.extend(found_elements)
                except etree.XPathEvalError:
                    pass

            if len(data_key_elements) == 0:
                if error_message:
                    error = error_message
                    if error not in self.error_messages:
                        self.error_messages.append(error)
                # else:
                #     error = "No xpath matching values for '{}' where found!".format(data_key)
                #     if error not in self.error_messages:
                #         self.error_messages.append(error)
            else:
                if data_key_match == "FIRST":
                    data_key_elements = [data_key_elements[0]]

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
        groups = regex_data["group"]
        match = regex_data["match"] if "match" in regex_data else "ALL"

        regexed_values = []
        for data in xpath_values:
            for expression in expressions:
                regex = re.compile(expression)
                matched_value = regex.search(str(data))
                if matched_value:
                    result_gps = {}
                    for group_num, gps_part in groups.items():
                        result_gps[gps_part] = matched_value.group(int(group_num))

                    if "Lat" in result_gps and "Lon" in result_gps:
                        found_gps = "{},{}".format(str(result_gps["Lat"]), str(result_gps["Lon"]))
                        regexed_values.append(found_gps)

        if len(regexed_values) == 0:
            error = "No regex matching values for '{}' where found!".format(data_key)
            if error not in self.error_messages:
                self.error_messages.append(error)
        else:
            if match == "FIRST":
                regexed_values = [regexed_values[0]]

        return regexed_values

    def _get_correct_counts(self, data_key: str, regex_result: list) -> str:
        if data_key == "datetime":
            return json.dumps(regex_result, ensure_ascii=False)
        if data_key == "types":
            return json.dumps(regex_result, ensure_ascii=False)

        if len(regex_result) > 1:
            self.error_messages.append("Data key '{}' doesn't expect more than one result value!".format(data_key))

        return regex_result[0]
