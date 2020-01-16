import json
import os
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from bin.utils.vismo_research.download_sites import VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH

VISMO_RESEARCH_GET_STATS_OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "get_stats_output.json")


def has_events(html_file_path: str) -> bool:
    """
    Checks a HTML content at html_file_path to find out if website is able to have events.

    :param html_file_path: a path to a file with a website's HTML content
    :return: False, if website doesn't have a calendar or there is a "no-events" warning;
             True, otherwise
    """

    with open(html_file_path, 'r') as content:
        document = BeautifulSoup(content, 'html.parser')
        calendar = document.find('div', {'id': 'kalendarAkci'})

        if calendar is not None:
            warning = calendar.find('span', {'class': 'vystraha'})

            if warning is None:
                return True

        return False


def sort_function(url: str) -> str:
    """
    A function for sorting URLS by their domains.

    :param url: an URL to parse
    :return: a domain string for alphabetical sorting
    """

    domain = urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

    return domain


def prepare_output(description: str, num_of_sites: int, list_of_sites: list) -> dict:
    """
    Prepares a dictionary for one of the stats for an output file.

    :param description: a name of the specific statistics
    :param num_of_sites: a count of sites complying with the description
    :param list_of_sites: a list of the sites' URLs
    :return: a dict combining the info
    """

    list_of_sites.sort(key=sort_function)

    return {
        description: {
            "count": num_of_sites,
            "list": list_of_sites
        }
    }


def get_statistics() -> None:
    """
    Gets statistics about Vismo websites from VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH
        (unreachable sites, sites without /ap page, sites without calendar, valid sites).
    Outputs VISMO_RESEARCH_GET_STATS_OUTPUT_FILE_PATH with these statistics.
    """

    without_ap_page_sites, error_sites, without_calendar_sites, with_calendar_sites = 0, 0, 0, 0
    without_ap_page_sites_list, error_sites_list, without_calendar_sites_list, with_calendar_sites_list = [], [], [], []

    with open(VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH, 'r') as json_file:
        data = json.load(json_file)

    for site in data:
        result = "NOK"

        if site["response_code"] is None:
            error_sites += 1
            error_sites_list.append(site["url"])

        elif site["response_code"] == 200:

            if has_events(site["html_file_path"]):
                result = "OK"
                with_calendar_sites += 1
                with_calendar_sites_list.append(site["url"])

            else:
                without_calendar_sites += 1
                without_calendar_sites_list.append(site["url"])

        else:
            without_ap_page_sites += 1
            without_ap_page_sites_list.append(site["url"])

        print("Checked URL", site["url"], "...", result)

    all_sites = without_ap_page_sites + error_sites + without_calendar_sites + with_calendar_sites
    statistics = [
        ("sites_with_error", error_sites, error_sites_list),
        ("sites_without_ap_page", without_ap_page_sites, without_ap_page_sites_list),
        ("sites_without_calendar", without_calendar_sites, without_calendar_sites_list),
        ("sites_with_calendar", with_calendar_sites, with_calendar_sites_list),
    ]

    with open(VISMO_RESEARCH_GET_STATS_OUTPUT_FILE_PATH, 'w') as output_file:
        output = {}

        for stat in statistics:
            output.update(prepare_output(stat[0], stat[1], stat[2]))

        output_file.write(json.dumps({
            "count_all": all_sites,
            "statistics": output
        }, indent=4))


if __name__ == '__main__':
    get_statistics()
