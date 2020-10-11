import json
import sqlite3
import urllib.parse as urllib
from typing import Union, Optional

import requests

from lib.constants import DATABASE_PATH, INPUT_SITES_BASE_FILE_PATH


def create_connection() -> sqlite3.Connection:
    """ Creates SQLite3 Connection to the database.

    :return: the SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except sqlite3.Error as e:
        print("Error occurred while creating a connection to the DB: {}".format(str(e)))


def generate_domain_name(url: str) -> str:
    """ Generates a domain name from the specified url address.

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


def get_base_by(attr: str, value: str = None) -> list:
    """ Gets a base information for the specified value of the specified attribute.

    :param attr: a key to search by
    :param value: a value for the key; if None fetches dict containing the 'attr' key
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


def get_active_base() -> list:
    return get_base_by('url')


def get_base_with_default_gps() -> [dict]:
    return get_base_by("default_gps")


def get_base_with_default_location() -> [dict]:
    return get_base_by("default_location")


def get_base_by_domain(value: str) -> Optional[dict]:
    base_list = get_base_by("domain", value)

    if len(base_list) == 0:
        return None
    elif len(base_list) == 1:
        return base_list[0]
    else:
        raise Exception("Specified domain is not unique: {}".format(value))


def get_base_by_url(value: str) -> Optional[dict]:
    base_list = get_base_by("url", value)

    if len(base_list) == 0:
        base_list = get_base_by("old_urls", value)

    if len(base_list) == 0:
        return None
    elif len(base_list) == 1:
        return base_list[0]
    else:
        raise Exception("Specified URL is not unique: {}".format(value))


def get_base_dict_per_url(base: list = None) -> dict:
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
    :param dry_run: a flag that determines whether to download a file
    :return: a result of the download process
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
        result = "Exception: {}".format(str(e))

    return result


def store_to_json_file(output: Union[list, dict], file_path: str) -> None:
    """ Saves the output into a json file at the specified file path.

    :param output: an output to be saved, either a dict or a list
    :param file_path: a file path of an output json file
    """
    with open(file_path, 'w') as output_file:
        output_file.write(json.dumps(output, indent=4, ensure_ascii=False))


def check_db(db_type: str, connection: sqlite3.Connection, names: list) -> list:
    """Checks if specified views or tables exist in the database.

    :param db_type: table or view
    :param connection: connection to the desired database
    :param names: names of tables/views
    :return: list of missing tables/views (empty, if all specified tables/views exist)
    """
    possible_types = ['table', 'view']
    if db_type not in possible_types:
        raise Exception("Unknown type: '{}' - must be one of {}".format(db_type, possible_types))

    names_count = len(names)
    if names_count == 0:
        return []
    elif names_count == 1:
        names_value = "('{}')".format(names[0])
    else:
        names_value = "({})".format(",".join("'{}'".format(name) for name in names))

    query = '''SELECT name FROM sqlite_master WHERE type='{}' AND name IN {}'''.format(db_type, names_value)
    cursor = connection.execute(query)
    db_names = [row[0] for row in cursor.fetchall()]

    if len(db_names) == len(names):
        return []
    else:
        missing_names = [name for name in names if name not in db_names]
        return missing_names


def check_db_views(connection: sqlite3.Connection, views: list) -> list:
    return check_db("view", connection, views)


def check_db_tables(connection: sqlite3.Connection, tables: list) -> list:
    return check_db("table", connection, tables)
