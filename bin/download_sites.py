import json
import os
import sqlite3
import traceback
from sqlite3 import Error
from urllib.parse import urlparse

import requests

DATA_DIR_PATH = "data/html_content"


def create_connection(db_file: str) -> sqlite3.Connection:
    connection = None

    try:
        connection = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return connection


def setup_db(connection: sqlite3.Connection):
    connection.execute("pragma foreign_keys = on")

    with open("resources/schema.sql", 'r') as file:
        for command in file.read().split(";"):
            connection.execute(command)

        connection.commit()


def download_sites():
    connection = create_connection("data/map_of_events.db")

    with connection:
        setup_db(connection)

        with open("resources/input_sites_base.json", 'r') as base_file:
            base_dict = json.load(base_file)
            input_urls = [base["url"].strip() for base in base_dict]

            os.makedirs(DATA_DIR_PATH, exist_ok=True)
            for url in input_urls:
                domain = urlparse(url).hostname
                domain = domain.replace("www.", "").replace(".", "_").replace("-", "_")

                try:
                    r = requests.get(url, timeout=30)
                    print("Downloading URL", url, "...", r.status_code)

                    if r.status_code == 200:
                        html_file_path = os.path.join(DATA_DIR_PATH, domain + ".html")

                        with open(html_file_path, 'w') as f:
                            f.write(str(r.text))

                        sql_command = ''' INSERT INTO websites(url, html_file_path)
                                          VALUES(?, ?) '''
                        values = (url, html_file_path)

                        connection.execute(sql_command, values)

                except Exception as e:
                    print("Downloading URL", url, "...", "Exception:")
                    traceback.print_exc()


if __name__ == '__main__':
    download_sites()
