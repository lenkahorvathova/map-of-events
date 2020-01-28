import json

from bin.utils.vismo_research.compute_statistics import ComputeStatistics
from lib import utils
from lib.constants import INPUT_SITES_BASE_FILE_PATH


class GenerateInput:
    """ Generates the first base file of input websites from usable Vismo URLs for main scripts. """

    def run(self) -> None:
        usable_urls = self.get_usable_urls()
        output_list = self.prepare_output(usable_urls)
        utils.store_to_json_file(output_list, INPUT_SITES_BASE_FILE_PATH)  # This overwrites the original base file!

    @staticmethod
    def get_usable_urls() -> list:
        with open(ComputeStatistics.OUTPUT_FILE_PATH, 'r') as statistics_file:
            statistics_dict = json.load(statistics_file)

        return statistics_dict["statistics"]["sites_with_calendar"]["list"]

    @staticmethod
    def prepare_output(usable_urls: list) -> list:
        output = []

        for url in usable_urls:
            domain = utils.get_domain_name(url)
            website_dict = {
                "domain": domain,
                "url": url,
                "parser": "vismo"
            }
            output.append(website_dict)

        return output


if __name__ == '__main__':
    generate_input = GenerateInput()
    generate_input.run()
