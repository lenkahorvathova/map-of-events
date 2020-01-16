import json
import os
import traceback
from datetime import datetime
from urllib.parse import urljoin

import requests
from lxml import etree

from lib.utils import create_connection

INPUT_SITES_BASE_FILE_PATH = "resources/input_sites_base.json"
DATA_DIR_PATH = "data/html_content"
TEMPLATES_DIR_PATH = "resources/xpaths"
DOWNLOAD_EVENTS_OUTPUT_FILE_PATH = "data/tmp/download_events_output.json"

with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
    BASE_DICT = json.load(base_file)


def get_base(url: str) -> None:
    """
    Gets information from input base file about websites.

    :param url: an URL address of website by which it gets rest of the info
    """

    for obj in BASE_DICT:
        if obj['url'] == url:
            return obj


def get_xpaths(xpath_file_path: str) -> dict:
    """
    Gets information from a template file and creates dictionary for it.

    :param xpath_file_path: a file path of the template file
    :return: a dictionary with info from the template
    """

    xpath_dict = {}

    with open(xpath_file_path) as xpath_file:
        for line in xpath_file:
            key, xpath = line.split(' ', 1)
            xpath_dict[key] = xpath.strip()

    return xpath_dict


def download_events() -> None:
    """
    Downloads HTML contents of pages with events of the input websites
        from DATA_DIR_PATH/<<domain>>/ directory into DATA_DIR_PATH/<<domain>>/events/<<downloaded_at>>.html.
    Stores a events' HTML file paths and timestamps of a download into the database.
    Outputs DOWNLOAD_EVENTS_OUTPUT_FILE_PATH with info about most recent run of the script.
    """

    connection = create_connection()
    log_output = []

    with connection:
        cursor = connection.execute('''SELECT url FROM websites''')
        input_urls = [url[0] for url in cursor.fetchall()]

        for url in input_urls:
            base = get_base(url)
            domain = base["domain"]
            parser = base["parser"]

            log_site_obj = {
                "domain": domain,
                "files": []
            }

            xpaths = get_xpaths(os.path.join(TEMPLATES_DIR_PATH, parser))
            current_dir = os.path.join(DATA_DIR_PATH, domain)

            for filename in os.listdir(current_dir):

                log_file_obj = {
                    "name": filename,
                    "events_list": []
                }

                with open(os.path.join(current_dir, filename)) as html_file:
                    dom = etree.parse(html_file, etree.HTMLParser())
                    root = dom.xpath(xpaths["root"])[0]

                    for el in root.xpath(xpaths["url"]):
                        event_url = urljoin(url, el)

                        log_file_obj["events_list"].append(event_url)

                        try:
                            html_file_dir = os.path.join(DATA_DIR_PATH, domain, "events")
                            os.makedirs(html_file_dir, exist_ok=True)

                            r = requests.get(event_url, timeout=30)

                            print("Downloading URL", event_url, "...", r.status_code)

                            if r.status_code == 200:
                                current_date = datetime.now()
                                file_name = current_date.strftime("%Y-%m-%d_%H-%M-%S")

                                html_file_path = os.path.join(html_file_dir, file_name + ".html")

                                with open(html_file_path, 'w') as f:
                                    f.write(str(r.text))

                                sql_command = ''' INSERT INTO events_raw(url, html_file_path)
                                                  VALUES(?, ?) '''
                                values = (event_url, html_file_path)

                                connection.execute(sql_command, values)

                        except Exception:
                            print("Downloading URL", event_url, "...", "Exception:")
                            traceback.print_exc()

                    log_file_obj["events_count"] = len(log_file_obj["events_list"])

                log_site_obj["files"].append(log_file_obj)

            log_output.append(log_site_obj)

    with open(DOWNLOAD_EVENTS_OUTPUT_FILE_PATH, 'w') as output_file:
        output_file.write(json.dumps(log_output, indent=4))


if __name__ == '__main__':
    download_events()
