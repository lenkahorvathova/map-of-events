import json

from bin.utils.vismo_research.get_statistics import GetStatistics
from lib.constants import INPUT_SITES_BASE_FILE_PATH
from lib.utils import get_domain_name


class GenerateInput:
    """ Generates a base file of input websites from usable Vismo URLs for main scripts. """

    def run(self) -> None:
        usable_urls = self.get_usable_urls()
        self.store_results(usable_urls)

    @staticmethod
    def get_usable_urls() -> list:
        with open(GetStatistics.OUTPUT_FILE_PATH, 'r') as statistics_file:
            statistics_dict = json.load(statistics_file)

        return statistics_dict["statistics"]["sites_with_calendar"]["list"]

    @staticmethod
    def store_results(usable_urls: list) -> None:
        output = []

        for url in usable_urls:
            output.append({
                "domain": get_domain_name(url),
                "url": url,
                "parser": "vismo"
            })

        # THIS OVERWRITES INPUT_SITES_BASE_FILE_PATH !
        # if you want a new input to be just appended at the end of the file, instead of 'w' use 'a' option
        with open(INPUT_SITES_BASE_FILE_PATH, 'w') as base_file:
            base_file.write(json.dumps(output, indent=4))


if __name__ == '__main__':
    get_statistics = GenerateInput()
    get_statistics.run()
