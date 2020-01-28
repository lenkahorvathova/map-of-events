import json
import os
import sqlite3
import urllib.parse as urllib

import requests

from lib.constants import DATABASE_PATH, INPUT_SITES_BASE_FILE_PATH, TEMPLATES_DIR_PATH


def create_connection() -> sqlite3.Connection:
    """ Creates SQLite3 Connection to the database.

    :return: the SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except sqlite3.Error as e:
        print("Error occurred while creating a connection to the DB: {}".format(str(e)))


def get_domain_name(url: str) -> str:
    """ Parses a domain name from the specified url address.

    Example:
        "http://www.belec-kreptov.cz/ap" -> "belec_kreptov_cz"

    :param url: an URL address
    :return: a domain name
    """

    domain = urllib.urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

    return domain


def load_base() -> list:
    """ Loads a base file with input websites' basic information.

    :return: a list of dictionaries with input website's info
    """

    with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
        base = json.load(base_file)

    return base


def get_base_by(attr: str, value: str) -> dict:
    """ Gets a base information for the specified value of the specified attribute.

    :param attr: a key to search by
    :param value: a value for the key
    :return: a dictionary with the base
    """

    for obj in load_base():
        if obj[attr] == value:
            return obj


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


def download_html_content(url: str, html_file_path: str, dry_run: bool = False) -> str:
    """ Downloads an HTML content from the specified URL to the specified file path.

    :param url: an URL address from where an HTML will be downloaded
    :param html_file_path: a path for a file to be created
    :param dry_run: a flag that determines whether to download a file
    :return: a result of the download process
    """

    try:
        r = requests.get(url, timeout=30)

        if not dry_run and r.status_code == 200:
            with open(html_file_path, 'w') as f:
                f.write(str(r.text))

        result = str(r.status_code)

    except Exception as e:
        result = "Exception: {}".format(str(e))

    return result


def store_to_json_file(output, file_path: str) -> None:
    """ Saves the output into a json file at the specified file path.

    :param output: an output to be saved (type not specified, but must be valid for json.dumps)
    :param file_path: a file path of an output json file
    """
    with open(file_path, 'w') as output_file:
        output_file.write(json.dumps(output, indent=4))
