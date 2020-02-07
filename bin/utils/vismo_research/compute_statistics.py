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

    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "compute_statistics_output2.json")

    def run(self) -> None:
        statistics_results = self.compute_statistics()
        output_dict = self.prepare_output(statistics_results)
        utils.store_to_json_file(output_dict, ComputeStatistics.OUTPUT_FILE_PATH)

    @staticmethod
    def compute_statistics() -> list:
        """ Analyses downloaded HTML contents and prepares resulting statistics about Vismo websites.

        :return: a list of prepared statistics tuples for an output file (statistic's description, count, list)
        """

        error_sites_count, error_sites_list = 0, []
        without_ap_page_sites_count, without_ap_page_sites_list = 0, []
        without_calendar_sites_count, without_calendar_sites_list = 0, []
        with_calendar_sites_count, with_calendar_sites_list = 0, []

        with open(DownloadCalendars.OUTPUT_FILE_PATH, 'r', encoding="utf-8") as json_file:
            download_info = json.load(json_file)

        for website in download_info:
            domain = utils.get_domain_name(website["url"])
            print("Checking domain:", domain, end="")

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

            print(" ({})".format(result))

        statistics_results = [
            ("sites_with_error", error_sites_count, error_sites_list),
            ("sites_without_ap_page", without_ap_page_sites_count, without_ap_page_sites_list),
            ("sites_without_calendar", without_calendar_sites_count, without_calendar_sites_list),
            ("sites_with_calendar", with_calendar_sites_count, with_calendar_sites_list),
        ]

        return statistics_results

    @staticmethod
    def has_calendar(html_file_path: str) -> bool:
        with open(html_file_path, 'r', encoding="utf-8") as content:
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
        all_sites_count = 0
        output = {}

        for statistic_tuple in statistics_results:
            description, sites_count, sites_list = statistic_tuple

            sites_list.sort(key=utils.get_domain_name)
            statistic_dict = {
                description: {
                    "count": sites_count,
                    "list": sites_list
                }
            }

            all_sites_count += sites_count
            output.update(statistic_dict)

        return {
            "count_all": all_sites_count,
            "statistics": output
        }


if __name__ == '__main__':
    compute_statistics = ComputeStatistics()
    compute_statistics.run()
