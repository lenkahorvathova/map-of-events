import json
import os
import traceback
from datetime import datetime

import requests

from lib.utils import create_connection, setup_db

DATABASE_PATH = "data/map_of_events.db"
INPUT_SITES_BASE_FILE_PATH = "resources/input_sites_base.json"
DATA_DIR_PATH = "data/html_content"


def download_sites() -> None:
    """
    Downloads HTML contents of main pages of the input websites
        specified in the INPUT_SITES_BASE_FILE_PATH
        into DATA_DIR_PATH/<<domain>>/<<downloaded_at>>.html.
    Stores a website's HTML file path and timestamp of a download into the database.
    """

    connection = create_connection(DATABASE_PATH)

    with connection:
        setup_db(connection)

        with open(INPUT_SITES_BASE_FILE_PATH, 'r') as base_file:
            base_dict = json.load(base_file)
            input_urls = [(base["url"].strip(), base["domain"].strip()) for base in base_dict]

            for url, domain in input_urls:

                try:
                    html_file_dir = os.path.join(DATA_DIR_PATH, domain)
                    os.makedirs(html_file_dir, exist_ok=True)

                    r = requests.get(url, timeout=30)

                    print("Downloading URL", url, "...", r.status_code)

                    if r.status_code == 200:
                        current_date = datetime.now()
                        file_name = current_date.strftime("%Y-%m-%d_%H-%M-%S")
                        html_file_path = os.path.join(html_file_dir, file_name + ".html")

                        with open(html_file_path, 'w') as f:
                            f.write(str(r.text))

                        sql_command = '''
                            INSERT INTO websites(url, html_file_path)
                            VALUES (?, ?)
                        '''
                        values = (url, html_file_path)

                        connection.execute(sql_command, values)

                except Exception:
                    print("Downloading URL", url, "...", "Exception:")
                    traceback.print_exc()


if __name__ == '__main__':
    download_sites()
