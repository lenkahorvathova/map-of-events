import os

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

        for input_website in self.base_dict:
            html_file_dir = os.path.join(DATA_DIR_PATH, input_website["domain"])
            info_to_insert = utils.download_html_content(input_website["url"], html_file_dir)

            if info_to_insert:
                websites_to_insert.append(info_to_insert)

        return websites_to_insert

    def store_to_database(self, websites_to_insert: list) -> None:
        with self.connection:
            for website_info in websites_to_insert:
                url, html_file_path = website_info

                sql_command = '''
                    INSERT INTO websites(url, html_file_path)
                    VALUES (?, ?)
                '''
                values = (url, html_file_path)

                self.connection.execute(sql_command, values)

            self.connection.commit()


if __name__ == '__main__':
    download_sites = DownloadCalendars()
    download_sites.run()
