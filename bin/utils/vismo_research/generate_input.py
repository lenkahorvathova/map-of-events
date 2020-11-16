import json
import os
from typing import List

from bin.utils.vismo_research.compute_statistics import ComputeStatistics
from lib import utils
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH


class GenerateInput:
    """ Generates base information of usable Vismo URLs to be used for main scripts. """

    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "input_vismo_calendars.json")

    def run(self) -> None:
        usable_urls = self.get_usable_urls()
        output_list = self.prepare_output(usable_urls)
        utils.store_to_json_file(output_list, GenerateInput.OUTPUT_FILE_PATH)

    @staticmethod
    def get_usable_urls() -> List[str]:
        with open(ComputeStatistics.OUTPUT_FILE_PATH, 'r', encoding="utf-8") as statistics_file:
            statistics_dict = json.load(statistics_file)

        return statistics_dict["statistics"]["sites_with_calendar"]["list"]

    @staticmethod
    def prepare_output(usable_urls: List[str]) -> List[dict]:
        output = []

        for url in usable_urls:
            website_dict = {
                "domain": utils.generate_domain_name(url),
                "url": url,
                "parser": "vismo"
            }
            output.append(website_dict)

        return output


if __name__ == '__main__':
    generate_input = GenerateInput()
    generate_input.run()
