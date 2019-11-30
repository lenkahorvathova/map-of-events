import json
import os
from datetime import datetime
from multiprocessing import Pool
from urllib.parse import urlparse

import requests

VISMO_RESEARCH_DIR_PATH = "data/tmp/vismo_research"


def download_sites_helper(url: str) -> dict:
    domain = urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

    info = {
        "url": url,
        "downloaded_at": str(datetime.now().timestamp())
    }

    try:
        r = requests.get(url, timeout=30)
        print("Downloading URL", url, "...", r.status_code)

        if r.status_code == 200:
            html_file_path = os.path.join(VISMO_RESEARCH_DIR_PATH, "html_content", domain + ".html")

            with open(html_file_path, 'w') as f:
                f.write(str(r.text))

            info["html_file_path"] = html_file_path

        info["response_code"] = r.status_code

    except Exception as e:
        print("Downloading URL", url, "...", "Exception")

        info["response_code"] = None
        info["exception"] = str(e)

    return info


def download_sites():
    with open("resources/research/vismo_urls.txt", 'r') as vismo_urls:
        input_urls = [line.strip() for line in vismo_urls]

        os.makedirs(os.path.join(VISMO_RESEARCH_DIR_PATH, "html_content"), exist_ok=True)
        with Pool(5) as p:
            sites = p.map(download_sites_helper, input_urls)

    with open(os.path.join(VISMO_RESEARCH_DIR_PATH, "sites_data.json"), 'w') as g:
        g.write(json.dumps(sites, indent=4))


if __name__ == '__main__':
    download_sites()
