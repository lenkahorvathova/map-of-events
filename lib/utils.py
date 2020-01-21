import json
import os
import sqlite3
import traceback
from datetime import datetime
from sqlite3 import Error
from urllib.parse import urlparse

import requests

from lib.constants import INPUT_SITES_BASE_FILE_PATH, TEMPLATES_DIR_PATH

DATABASE_PATH = "data/map_of_events.db"


def create_connection() -> sqlite3.Connection:
    """ Creates the SQLite3 Connection to the database.

    :return: the SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except Error as error:
        print(error)


def get_domain_name(url: str) -> str:
    """ Parses a domain name from the specified url address.

    Example:
        "http://www.belec-kreptov.cz/ap" -> "belec_kreptov_cz"

    :param url: an URL address
    :return: a domain name
    """

    domain = urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

    return domain


def load_base() -> list:
    """ Loads a base file with input websites' basic information.

    :return: a list of dictionaries with input website's info
    """

    with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
        base = json.load(base_file)

    return base


def get_xpaths(parser: str) -> dict:
    """ Gets information from a template file of the parser and creates a dictionary for it.

    :param parser: a string specifying a template file with defined xpaths
    :return: a dictionary with xpaths from the template
    """

    xpath_file_path = os.path.join(TEMPLATES_DIR_PATH, parser)
    xpath_dict = {}

    with open(xpath_file_path) as xpath_file:
        for line in xpath_file:
            key, xpath = line.split(' ', 1)
            xpath_dict[key] = xpath.strip()

    return xpath_dict


def download_html_content(url: str, html_file_dir: str) -> (str, str):
    """ Tries to download an HTML content from the specified URL.

    A file name used for an HTML file is datetime of the download.

    :param url: an URL address from where an HTML will be downloaded
    :param html_file_dir: a directory to where an HTML file will be saved
    :return: information to be stored in a DB (url, html_file_path)
    """

    info_to_insert = None

    print("Downloading URL", url, "... ", end="")

    try:
        os.makedirs(html_file_dir, exist_ok=True)

        r = requests.get(url, timeout=30)

        if r.status_code == 200:
            current_date = datetime.now()
            file_name = current_date.strftime("%Y-%m-%d_%H-%M-%S")
            html_file_path = os.path.join(html_file_dir, file_name + ".html")

            with open(html_file_path, 'w') as f:
                f.write(str(r.text))

            info_to_insert = (url, html_file_path)

        print(r.status_code)

    except Exception:
        print("Exception:")
        traceback.print_exc()

    return info_to_insert


def store_to_json_file(output, file_path: str) -> None:
    """ Saves the output into a json file at the specified file path.

    :param output: an output to be saved (type not specified, but must be valid for json.dumps)
    :param file_path: a file path of an output json file
    """
    with open(file_path, 'w') as output_file:
        output_file.write(json.dumps(output, indent=4))
