import os
from datetime import datetime
from multiprocessing import Pool

import requests

from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH
from lib.utils import get_domain_name, store_to_json_file


class DownloadCalendars:
    """ Downloads an HTML content of a calendar page of input Vismo websites.

    Uses multiprocessing to speed up the process.
    Outputs a json file with information from a downloading process about each website.
    """

    INPUT_URLS_FILE_PATH = "resources/research/vismo_urls.txt"
    HTML_CONTENT_DIR_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "html_content")
    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "download_calendars_output.json")

    def run(self) -> None:
        input_urls = self.load_input_urls()
        download_info = self.download_calendars(input_urls)
        store_to_json_file(download_info, DownloadCalendars.OUTPUT_FILE_PATH)

    @staticmethod
    def load_input_urls() -> list:
        with open(DownloadCalendars.INPUT_URLS_FILE_PATH, 'r') as vismo_urls:
            return [line.strip() for line in vismo_urls]

    @staticmethod
    def download_calendars(input_urls: list) -> list:
        os.makedirs(DownloadCalendars.HTML_CONTENT_DIR_PATH, exist_ok=True)

        with Pool(5) as p:
            return p.map(DownloadCalendars.download_html_content, input_urls)

    @staticmethod
    def download_html_content(url: str) -> dict:
        """ Tries to download an HTML content from the specified URL.

        :param url: a website's URL address with a calendar (e.g. http://dolnibezdekov.cz/ap)
        :return: results from a downloading process (url, downloaded_at, response_code, -/html_file_path/exception)
        """

        domain = get_domain_name(url)
        info = {
            "url": url,
            "downloaded_at": str(datetime.now())
        }

        print("Downloading URL", url, "... ", end="")

        try:
            r = requests.get(url, timeout=30)
            info["response_code"] = r.status_code

            if r.status_code == 200:
                html_file_path = os.path.join(DownloadCalendars.HTML_CONTENT_DIR_PATH, domain + ".html")
                info["html_file_path"] = html_file_path

                with open(html_file_path, 'w') as html_file:
                    html_file.write(str(r.text))

            print(r.status_code)

        except Exception as e:
            info["response_code"] = None
            info["exception"] = str(e)

            print("Exception")

        return info


if __name__ == '__main__':
    download_calendars = DownloadCalendars()
    download_calendars.run()
