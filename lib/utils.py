import json
import os
import sqlite3
import sys
import urllib.parse as urllib
from typing import Union, Optional, List

import requests

from lib.constants import DATABASE_PATH, INPUT_SITES_BASE_FILE_PATH
from lib.logger import set_up_script_logger

LOGGER = set_up_script_logger(__file__)


def create_connection() -> sqlite3.Connection:
    """ Creates SQLite3 Connection to the database.

    :return: the SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except sqlite3.Error as e:
        LOGGER.critical("Error occurred while creating a connection to the DB: {}".format(str(e)))
        sys.exit()


def generate_domain_name(url: str) -> str:
    """ Generates a domain name string from the specified URL address.
    Example: "http://www.belec-kreptov.cz/ap" -> "belec_kreptov_cz"

    :param url: an URL address
    :return: a domain name string
    """

    domain = urllib.urlparse(url).hostname
    domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")
    return domain


def load_base() -> List[dict]:
    """ Loads a base file with input websites' basic information.

    :return: a list of dictionaries with input website's information
    """

    with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
        return json.load(base_file)


def _get_base_by(attr: str, value: str = None) -> List[dict]:
    """ Gets base information for the specified value of the specified attribute.

    :param attr: a key to search by
    :param value: a value for the key;
                  if None, fetches dictionary containing the key
    :return: a list of dictionaries with the base
    """

    result = []
    for obj in load_base():
        if value is None:
            if attr in obj:
                result.append(obj)
        else:
            attr_value = obj.get(attr, None)
            if attr_value is not None and (attr_value == value or value in attr_value):
                result.append(obj)
    return result


def get_active_base() -> List[dict]:
    """ Gets base information of active calendars (containing 'url' key). """

    return _get_base_by('url')


def get_base_with_default_gps() -> List[dict]:
    """ Gets base information of calendars with default GPS (containing 'default_gps' key). """

    return _get_base_by("default_gps")


def get_base_with_default_location() -> List[dict]:
    """ Gets base information of calendars with default location (containing 'default_location' key). """

    return _get_base_by("default_location")


def get_base_by_domain(value: str) -> Optional[dict]:
    """ Gets base information of a calendar with the specified domain string.

    :param value: a calendar's domain string
    :return: a dictionary with the calendar's base;
             None, if the specified domain is incorrect or not unique
    """

    base_list = _get_base_by("domain", value)
    if len(base_list) == 0:
        return None
    elif len(base_list) == 1:
        return base_list[0]
    else:
        exception_msg = "Value wasn't correctly specified or is not unique: {}".format(value)
        LOGGER.critical(exception_msg)
        raise Exception(exception_msg)


def get_base_by_url(value: str) -> Optional[dict]:
    """ Gets base information of a calendar with the specified URL address.

    :param value: a calendar's URL address
    :return: a dictionary with the calendar's base;
             None, if the specified URL is incorrect or not unique
    """

    base_list = _get_base_by("url", value)
    if len(base_list) == 0:
        base_list = _get_base_by("old_urls", value)

    if len(base_list) == 0:
        return None
    elif len(base_list) == 1:
        return base_list[0]
    else:
        exception_msg = "Value wasn't correctly specified or is not unique: {}".format(value)
        LOGGER.critical(exception_msg)
        raise Exception(exception_msg)


def get_base_dict_per_url(base: list = None) -> dict:
    """ Gets base information of input calendars in a form of dictionary with their URLs as keys.

    :param base: a list of dictionaries to use as a base
    :return: a dictionary with the calendars' bases
    """

    if base is None:
        base = load_base()

    base_dict = {}
    for calendar_base in base:
        calendar_url = calendar_base.get('url', None)
        if calendar_url:
            base_dict[calendar_url] = calendar_base
        calendar_urls = calendar_base.get('old_urls', [])
        for calendar_url in calendar_urls:
            base_dict[calendar_url] = calendar_base

    return base_dict


def download_html_content(url: str, html_file_path: str, encoding: str = None, dry_run: bool = False) -> str:
    """ Downloads an HTML content from the specified URL to the specified file path.

    :param url: an URL address from where an HTML will be downloaded
    :param html_file_path: a path for a file to be created
    :param encoding: a desired encoding for the request specified in the base file
    :param dry_run: a flag that determines whether to download a file or just to check URL response
    :return: a result of the download process (request's status code)
    """

    try:
        r = requests.get(url, timeout=30)

        if encoding is not None:
            r.encoding = encoding

        if not dry_run and r.status_code == 200:
            with open(html_file_path, 'w', encoding="utf-8") as f:
                f.write(r.text)

        result = str(r.status_code)

    except Exception as e:
        result = getattr(e, 'message', repr(e))
        LOGGER.error("Exception: {}".format(result))

    return result


def store_to_json_file(output: Union[list, dict], file_path: str) -> None:
    """ Saves the output into a json file at the specified file path.

    :param output: an output to be saved, either a dict or a list
    :param file_path: a file path of an output json file
    """

    with open(file_path, 'w') as output_file:
        output_file.write(json.dumps(output, indent=4, ensure_ascii=False))


def _check_db(db_type: str, connection: sqlite3.Connection, names: List[str]) -> None:
    """Checks if the specified views or tables exist in the database.

    :param db_type: a table or a view
    :param connection: a connection to the desired database
    :param names: names of tables/views to check
    """

    possible_types = ['table', 'view']
    if db_type not in possible_types:
        exception_msg = "Unknown type: '{}' - must be one of {}".format(db_type, possible_types)
        LOGGER.critical(exception_msg)
        raise Exception(exception_msg)

    names_count = len(names)
    if names_count == 0:
        return
    elif names_count == 1:
        names_value = "('{}')".format(names[0])
    else:
        names_value = "({})".format(",".join("'{}'".format(name) for name in names))

    query = '''SELECT name FROM sqlite_master WHERE type='{}' AND name IN {}'''.format(db_type, names_value)
    cursor = connection.execute(query)
    db_names = [row[0] for row in cursor.fetchall()]

    missing_names = [name for name in names if name not in db_names]
    if len(missing_names) != 0:
        exception_msg = "Missing {}s in the DB: {}".format(db_type, missing_names)
        LOGGER.critical(exception_msg)
        raise Exception(exception_msg)


def check_db_views(connection: sqlite3.Connection, views: List[str]) -> None:
    """Checks if the specified views exist in the database.

    :param connection: a connection to the desired database
    :param views: names of views to check
    """

    _check_db("view", connection, views)


def check_db_tables(connection: sqlite3.Connection, tables: List[str]) -> None:
    """Checks if the specified tables exist in the database.

    :param connection: a connection to the desired database
    :param tables: names of tables to check
    """

    _check_db("table", connection, tables)


def check_file(file_path: str) -> None:
    """Checks if the specified file exists.

    :param file_path: a path to the file to check
    """

    if not os.path.isfile(file_path):
        exception_msg = "Missing an input base file: '{}'".format(INPUT_SITES_BASE_FILE_PATH)
        LOGGER.critical(exception_msg)
        raise Exception(exception_msg)


def sanitize_string_for_html(input_string: str) -> Optional[str]:
    """ Sanitizes a string for an HTML document.

    :param input_string: a string to sanitize
    :return: a sanitized string
    """

    if not input_string:
        return None
    return input_string.replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"').replace('`', '\'')
