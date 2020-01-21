import json
import os

from bs4 import BeautifulSoup

from bin.utils.vismo_research.download_calendars import DownloadCalendars
from lib import utils
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH


class ComputeStatistics:
    """ Computes statistics about Vismo websites by analysing downloaded HTML contents of their calendar pages.

    Statistics - sites returning an error, sites without the Vismo '/ap' page,
        sites with the '/ap' page but without calendar, usable sites with calendar
    Outputs a json file with counts and lists for these statistics.
    """

    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "compute_statistics_output.json")

    def run(self) -> None:
        statistics_results = self.compute_statistics()
        utils.store_to_json_file(self.prepare_output(statistics_results), ComputeStatistics.OUTPUT_FILE_PATH)

    @staticmethod
    def compute_statistics() -> list:
        """ Analyses downloaded HTML contents and prepares resulting statistics about Vismo websites.

        :return: a list of prepared statistics tuples for an output file (statistic's description, count, list)
        """

        error_sites_count, error_sites_list = 0, []
        without_ap_page_sites_count, without_ap_page_sites_list = 0, []
        without_calendar_sites_count, without_calendar_sites_list = 0, []
        with_calendar_sites_count, with_calendar_sites_list = 0, []

        with open(DownloadCalendars.OUTPUT_FILE_PATH, 'r') as json_file:
            download_info = json.load(json_file)

        for website in download_info:
            print("Checking URL", website["url"], "... ", end="")

            result = "NOK"

            if website["response_code"] is None:
                error_sites_count += 1
                error_sites_list.append(website["url"])

            elif website["response_code"] == 200:

                if ComputeStatistics.has_calendar(website["html_file_path"]):
                    result = "OK"
                    with_calendar_sites_count += 1
                    with_calendar_sites_list.append(website["url"])

                else:
                    without_calendar_sites_count += 1
                    without_calendar_sites_list.append(website["url"])

            else:
                without_ap_page_sites_count += 1
                without_ap_page_sites_list.append(website["url"])

            print(result)

        statistics_results = [
            ("sites_with_error", error_sites_count, error_sites_list),
            ("sites_without_ap_page", without_ap_page_sites_count, without_ap_page_sites_list),
            ("sites_without_calendar", without_calendar_sites_count, without_calendar_sites_list),
            ("sites_with_calendar", with_calendar_sites_count, with_calendar_sites_list),
        ]

        return statistics_results

    @staticmethod
    def has_calendar(html_file_path: str) -> bool:
        with open(html_file_path, 'r') as content:
            document = BeautifulSoup(content, 'html.parser')

        calendar = document.find('div', {'id': 'kalendarAkci'})

        if calendar:
            warning = calendar.find('span', {'class': 'vystraha'})
            """ some websites contain a calendar but with a warning that its content is unavailable """

            if not warning:
                return True

        return False

    @staticmethod
    def prepare_output(statistics_results: list) -> dict:
        output = {}
        all_sites_count = 0

        for statistic_tuple in statistics_results:
            output.update(ComputeStatistics.prepare_statistic(statistic_tuple))
            all_sites_count += statistic_tuple[1]

        return {
            "count_all": all_sites_count,
            "statistics": output
        }

    @staticmethod
    def prepare_statistic(statistic_tuple: (str, int, list)) -> dict:
        description, sites_count, sites_list = statistic_tuple
        sites_list.sort(key=utils.get_domain_name)

        return {
            description: {
                "count": sites_count,
                "list": sites_list
            }
        }


if __name__ == '__main__':
    compute_statistics = ComputeStatistics()
    compute_statistics.run()
