import json

from bs4 import BeautifulSoup


def has_events(html_file_path):
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


def prepare_output(description, num_of_sites, list_of_sites, all_sites):
    return description + " " + str(num_of_sites) + "/" + str(all_sites) + "\n" \
           + str(list_of_sites) + "\n" \
           + "-----------------------------------------" + "\n"


def get_statistics():
    without_calendar_sites, error_sites, without_events_sites, with_events_sites = 0, 0, 0, 0
    without_calendar_sites_list, error_sites_list, without_events_sites_list, with_events_sites_list = [], [], [], []

    with open("data/tmp/vismo_research/sites_data.json") as json_file:
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
        ("Sites without calendar:", without_calendar_sites, without_calendar_sites_list),
        ("Sites with error:", error_sites, error_sites_list),
        ("Sites without events:", without_events_sites, without_events_sites_list),
        ("Sites with events:", with_events_sites, with_events_sites_list),
    ]

    with open("data/tmp/vismo_research/output.txt", 'w') as output_file:

        output_text = ""
        for stat in statistics:
            output_text += prepare_output(stat[0], stat[1], stat[2], all_sites)

        output_file.write(output_text)


if __name__ == '__main__':
    get_statistics()
