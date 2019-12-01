import json
import os
from urllib.parse import urlparse

VISMO_RESEARCH_DIR_PATH = "data/tmp/vismo_research"


def generate_input():
    with open(os.path.join(VISMO_RESEARCH_DIR_PATH, "output.json"), 'r') as statistics_file:
        statistics_dict = json.load(statistics_file)
        usable_urls = statistics_dict["statistics"]["sites_with_calendar"]["list"]

    output = []
    for url in usable_urls:
        domain = urlparse(url).hostname
        domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

        output.append({
            "domain": domain,
            "url": url,
            "parser": "vismo"
        })

    with open("resources/input_sites_base.json", 'w') as base_file:
        base_file.write(json.dumps(output, indent=4))


if __name__ == '__main__':
    generate_input()
