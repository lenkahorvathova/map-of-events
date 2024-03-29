import multiprocessing
import os
from datetime import datetime
from typing import List

import requests

from lib import utils
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH


class DownloadCalendars:
    """ Downloads a calendar page HTML content of Vismo websites. """

    INPUT_URLS_FILE_PATH = "resources/research/vismo_urls.txt"
    HTML_CONTENT_DIR_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "html_content")
    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "download_calendars_output.json")

    def run(self) -> None:
        input_urls = self.load_input_urls()
        download_info = self.download_calendars(input_urls)
        utils.store_to_json_file(download_info, DownloadCalendars.OUTPUT_FILE_PATH)

    @staticmethod
    def load_input_urls() -> List[str]:
        with open(DownloadCalendars.INPUT_URLS_FILE_PATH, 'r', encoding="utf-8") as vismo_urls:
            return [line.strip() for line in vismo_urls]

    @staticmethod
    def download_calendars(input_urls: List[str]) -> List[dict]:
        os.makedirs(DownloadCalendars.HTML_CONTENT_DIR_PATH, exist_ok=True)

        with multiprocessing.Pool(32) as p:
            return p.map(DownloadCalendars.download_html_content, input_urls)

    @staticmethod
    def download_html_content(url: str) -> dict:
        domain = utils.generate_domain_name(url)
        info = {
            "url": url,
            "downloaded_at": "{0:%Y-%m-%d %H:%M:%S}".format(datetime.now())
        }

        debug_output = "Downloading URL: " + str(url)

        try:
            r = requests.get(url, timeout=30)
            info["response_code"] = r.status_code

            if r.status_code == 200:
                html_file_path = os.path.join(DownloadCalendars.HTML_CONTENT_DIR_PATH, domain + ".html")
                info["html_file_path"] = html_file_path

                with open(html_file_path, 'w', encoding="utf-8") as html_file:
                    html_file.write(r.text)

            debug_output += " ({})".format(r.status_code)

        except Exception as e:
            info["response_code"] = None
            info["exception"] = str(e)

            debug_output += " (Exception)"

        print(debug_output)

        return info


if __name__ == '__main__':
    download_calendars = DownloadCalendars()
    download_calendars.run()
