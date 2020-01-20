import json
import os

from bs4 import BeautifulSoup

from bin.utils.vismo_research.download_sites import DownloadSites
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH
from lib.utils import get_domain_name


class GetStatistics:
    """ Gets statistics about Vismo websites by analysing downloaded HTML contents of calendar pages.

    Statistics - sites returning an error, sites without a Vismo '/ap' page,
        sites with an '/ap' page but without calendar, usable sites with calendar
    Outputs a json file with counts and lists for these statistics.
    """

    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "get_stats_output.json")

    def run(self) -> None:
        statistics_results = self.get_statistics()
        self.store_results(statistics_results)

    @staticmethod
    def get_statistics() -> list:
        """ Analyses downloaded HTML contents and prepares resulting statistics about Vismo websites.

        :return: a count of all Vismo websites and a list of prepared statistics tuples for an output file
        """

        error_sites_count, error_sites_list = 0, []
        without_ap_page_sites_count, without_ap_page_sites_list = 0, []
        without_calendar_sites_count, without_calendar_sites_list = 0, []
        with_calendar_sites_count, with_calendar_sites_list = 0, []

        with open(DownloadSites.OUTPUT_FILE_PATH, 'r') as json_file:
            downloaded_websites_info = json.load(json_file)

        for website in downloaded_websites_info:
            print("Checking URL", website["url"], "... ", end="")

            result = "NOK"

            if website["response_code"] is None:
                error_sites_count += 1
                error_sites_list.append(website["url"])

            elif website["response_code"] == 200:

                if GetStatistics.has_calendar(website["html_file_path"]):
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
    def store_results(statistics_results: list) -> None:
        output = {}
        all_sites_count = 0

        for statistic_tuple in statistics_results:
            output.update(GetStatistics.prepare_statistic_dict(statistic_tuple))
            all_sites_count += statistic_tuple[1]

        with open(GetStatistics.OUTPUT_FILE_PATH, 'w') as output_file:
            output_file.write(json.dumps({
                "count_all": all_sites_count,
                "statistics": output
            }, indent=4))

    @staticmethod
    def prepare_statistic_dict(statistic_tuple: (str, int, list)) -> dict:
        description, sites_count, sites_list = statistic_tuple
        sites_list.sort(key=get_domain_name)

        return {
            description: {
                "count": sites_count,
                "list": sites_list
            }
        }


if __name__ == '__main__':
    get_statistics = GetStatistics()
    get_statistics.run()
