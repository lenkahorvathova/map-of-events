import json
import os
from datetime import datetime
from multiprocessing import Pool
from urllib.parse import urlparse

import requests

from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH

VISMO_RESEARCH_INPUT_URLS_FILE_PATH = "resources/research/vismo_urls.txt"
VISMO_RESEARCH_HTML_CONTENT_DIR_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "html_content")
VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "download_sites_output.json")


def download_sites_helper(url: str) -> dict:
    """
    Tries to download an HTML content from specified URL.

    :param url: website's URL address
    :return: info from downloading (url, downloaded_at, response_code, html_file_path/exception)
    """

    domain = urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

    info = {
        "url": url,
        "downloaded_at": str(datetime.now().timestamp())
    }

    try:
        r = requests.get(url, timeout=30)
        info["response_code"] = r.status_code

        print("Downloading URL", url, "...", r.status_code)

        if r.status_code == 200:
            html_file_path = os.path.join(VISMO_RESEARCH_HTML_CONTENT_DIR_PATH, domain + ".html")
            info["html_file_path"] = html_file_path

            with open(html_file_path, 'w') as f:
                f.write(str(r.text))

    except Exception as e:
        print("Downloading URL", url, "...", "Exception")

        info["response_code"] = None
        info["exception"] = str(e)

    return info


def download_sites() -> None:
    """
    Downloads HTML contents of main pages of the input websites
        specified in the VISMO_RESEARCH_INPUT_URLS_FILE_PATH.
    Uses multiprocessing to speed up the process
        (a function executed in parallel across input URLs is "download_sites_helper").
    Outputs VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH with information about each website.
    """

    with open(VISMO_RESEARCH_INPUT_URLS_FILE_PATH, 'r') as vismo_urls:
        input_urls = [line.strip() for line in vismo_urls]

        os.makedirs(VISMO_RESEARCH_HTML_CONTENT_DIR_PATH, exist_ok=True)
        with Pool(5) as p:
            sites = p.map(download_sites_helper, input_urls)

    with open(VISMO_RESEARCH_DWNLD_SITES_OUTPUT_FILE_PATH, 'w') as g:
        g.write(json.dumps(sites, indent=4))


if __name__ == '__main__':
    download_sites()
