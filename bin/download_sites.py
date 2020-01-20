import os

from lib.constants import DATA_DIR_PATH
from lib.utils import create_connection, load_base, download_html_content


class DownloadSites:
    """ Downloads an HTML content of a calendar page of input websites specified in a base file
        and stores website's URL, HTML file path and timestamp of a download into the database. """

    def __init__(self) -> None:
        self.connection = create_connection()

    def run(self) -> None:
        input_sites_base = load_base()
        websites_to_insert = self.download_sites(input_sites_base)
        self.store_to_database(websites_to_insert)

    @staticmethod
    def download_sites(input_sites_base: list) -> list:
        websites_to_insert = []

        for input_site in input_sites_base:
            html_file_dir = os.path.join(DATA_DIR_PATH, input_site["domain"])
            info_to_insert = download_html_content(input_site["url"], html_file_dir)

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
    download_sites = DownloadSites()
    download_sites.run()
