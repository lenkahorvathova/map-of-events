import json
import os

from bs4 import BeautifulSoup

VISMO_RESEARCH_DIR_PATH = "data/tmp/vismo_research"


def has_events(html_file_path: str) -> bool:
    with open(html_file_path, 'r') as content:
        document = BeautifulSoup(content, 'html.parser')
        calendar = document.find('div', {'id': 'kalendarAkci'})

        if calendar is not None:
            events = calendar.find('ul', {'class': 'ui'})

            if events is not None:
                warning = calendar.find('span', {'class': 'vystraha'})

                if warning is None:
                    return True

        return False


def prepare_output(description: str, num_of_sites: int, list_of_sites: list) -> dict:
    return {
        description: {
            "count": num_of_sites,
            "list": list_of_sites
        }
    }


def get_statistics():
    without_calendar_sites, error_sites, without_events_sites, with_events_sites = 0, 0, 0, 0
    without_calendar_sites_list, error_sites_list, without_events_sites_list, with_events_sites_list = [], [], [], []

    with open(os.path.join(VISMO_RESEARCH_DIR_PATH, "sites_data.json"), 'r') as json_file:
        data = json.load(json_file)

    for site in data:
        result = "NOK"

        if site["response_code"] is None:
            error_sites += 1
            error_sites_list.append(site["url"])

        elif site["response_code"] == 200:

            if has_events(site["html_file_path"]):
                result = "OK"
                with_events_sites += 1
                with_events_sites_list.append(site["url"])

            else:
                without_events_sites += 1
                without_events_sites_list.append(site["url"])

        else:
            without_calendar_sites += 1
            without_calendar_sites_list.append(site["url"])

        print("Checked URL", site["url"], "...", result)

    all_sites = without_calendar_sites + error_sites + without_events_sites + with_events_sites
    statistics = [
        ("sites_without_calendar", without_calendar_sites, without_calendar_sites_list),
        ("sites_with_error", error_sites, error_sites_list),
        ("sites_without_events", without_events_sites, without_events_sites_list),
        ("sites_with_events", with_events_sites, with_events_sites_list),
    ]

    with open(os.path.join(VISMO_RESEARCH_DIR_PATH, "output.json"), 'w') as output_file:

        output = {}
        for stat in statistics:
            output.update(prepare_output(stat[0], stat[1], stat[2]))

        output_file.write(json.dumps({
            "all": all_sites,
            "statistics": output
        }, indent=4))


if __name__ == '__main__':
    get_statistics()
