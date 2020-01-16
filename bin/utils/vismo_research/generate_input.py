import json
import os
from urllib.parse import urlparse

VISMO_RESEARCH_DATA_DIR_PATH = "data/tmp/vismo_research"
VISMO_RESEARCH_GET_STATS_OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "get_stats_output.json")

INPUT_SITES_BASE_FILE_PATH = "resources/input_sites_base.json"


def generate_input() -> None:
    """
    Generates INPUT_SITES_BASE_FILE_PATH of valid Vismo websites for main scripts.
    """

    with open(VISMO_RESEARCH_GET_STATS_OUTPUT_FILE_PATH, 'r') as statistics_file:
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

    # THIS OVERWRITES INPUT_SITES_BASE_FILE_PATH !
    # if you want a new input to just append at the end of the file, instead of 'w' use 'a' option
    with open(INPUT_SITES_BASE_FILE_PATH, 'w') as base_file:
        base_file.write(json.dumps(output, indent=4))


if __name__ == '__main__':
    generate_input()
