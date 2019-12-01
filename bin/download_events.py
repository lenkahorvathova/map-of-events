import json
import os
import traceback
from datetime import datetime
from urllib.parse import urljoin

import requests
from lxml import etree

from lib.utils import create_connection, setup_db

DATA_DIR_PATH = "data/html_content"

with open("resources/input_sites_base.json", 'r') as base_file:
    base_dict = json.load(base_file)


def get_base(url: str):
    for obj in base_dict:
        if obj['url'] == url:
            return obj


def get_xpaths(xpath_file_path: str) -> dict:
    xpath_dict = {}

    with open(xpath_file_path) as xpath_file:
        for line in xpath_file:
            key, xpath = line.split(' ', 1)
            xpath_dict[key] = xpath.strip()

    return xpath_dict


def download_events():
    connection = create_connection("data/map_of_events.db")
    log_output = []

    with connection:
        setup_db(connection)

        cursor = connection.execute("SELECT url FROM websites")
        input_urls = cursor.fetchall()

        for url in input_urls:
            url = url[0]
            base = get_base(url)
            domain = base["domain"]
            parser = base["parser"]

            log_site_obj = {
                "domain": domain,
                "files": []
            }

            xpaths = get_xpaths(os.path.join("resources/xpaths", parser))

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

    with open("data/tmp/download_events_output.json", 'w') as output_file:
        output_file.write(json.dumps(log_output, indent=4))


if __name__ == '__main__':
    download_events()
