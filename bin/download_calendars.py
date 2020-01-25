import os
from datetime import datetime

from lib import utils
from lib.constants import DATA_DIR_PATH


class DownloadCalendars:
    """ Downloads an HTML content of a calendar page of input websites specified in a base file.

    Stores website's URL, HTML file path and timestamp of a download into the database.
    """

    def __init__(self) -> None:
        self.connection = utils.create_connection()
        self.base_dict = utils.load_base()

    def run(self) -> None:
        websites_to_insert = self.download_calendars()
        self.store_to_database(websites_to_insert)

    def download_calendars(self) -> list:
        websites_to_insert = []
        timestamp = datetime.now()

        index = 1
        all_count = len(self.base_dict)
        for input_website in self.base_dict:
            print("{}/{} | ".format(index, all_count), end="")
            index += 1

            url = input_website["url"]
            html_file_dir = os.path.join(DATA_DIR_PATH, input_website["domain"])
            html_file_name = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
            html_file_path = os.path.join(html_file_dir, html_file_name + ".html")

            try:
                utils.download_html_content(url, html_file_path)
                os.makedirs(html_file_dir, exist_ok=True)
                websites_to_insert.append((url, html_file_path, timestamp))

            except Exception:
                print("Something went wrong when downloading {}.".format(url))

        return websites_to_insert

    def store_to_database(self, websites_to_insert: list) -> None:
        with self.connection:
            for website_info in websites_to_insert:
                url, html_file_path, downloaded_at = website_info

                sql_command = '''
                    INSERT INTO website(url, html_file_path, downloaded_at)
                    VALUES (?, ?, ?)
                '''
                values = (url, html_file_path, downloaded_at)

                self.connection.execute(sql_command, values)

            self.connection.commit()


if __name__ == '__main__':
    download_sites = DownloadCalendars()
    download_sites.run()
