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
    """ Creates an SQLite3 Connection to the database.

    :return: SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except Error as error:
        print(error)


def get_domain_name(url: str) -> str:
    """ Parse a domain name from the specified url address.

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

    :return: a list of dictionaries with input websites' info
    """

    with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
        base = json.load(base_file)

    return base


def get_xpaths(parser: str) -> dict:
    """ Gets information from a template file for the parser and creates dictionary for it.

    :param parser: a string specifying a template file with xpaths to use
    :return: a dictionary with info from the template
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

    :param url: a URL address from where an HTML will be downloaded
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
