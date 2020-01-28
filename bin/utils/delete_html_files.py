import argparse
import os

from bin.download_events import DownloadEvents
from lib import utils
from lib.constants import DATA_DIR_PATH


class DeleteHTMLFiles:
    """ Deletes all the HTML files of the specified type an with a name starting with the specified timestamp. """

    FILE_TYPES = ["calendars", "events"]

    def __init__(self):
        self.args = self._parse_args()
        self.base = utils.load_base()

    @staticmethod
    def _parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--type', required=True, type=str, choices=DeleteHTMLFiles.FILE_TYPES,
                            help='Type of the HTML files to be deleted.')
        parser.add_argument('--timestamp', required=True, type=str,
                            help="Timestamp of the HTML files to be deleted. "
                                 "It can be as specific as needed (e.g. '2020-01-17', '2020-01-21_22-47-02').")
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="Doesn't store any output and only prints it to stdout.")
        parser.add_argument('--domain', type=str, default=None,
                            help="Domain of a website which HTML files will be deleted.")

        return parser.parse_args()

    def run(self) -> None:
        all_removed_files = []

        if self.args.domain:
            all_removed_files = self.delete_html_file(self.args.domain)
        else:
            for website in self.base:
                removed_files = self.delete_html_file(website["domain"])
                all_removed_files.extend(removed_files)

        debug_output = "{} files deleted"
        if self.args.dry_run:
            debug_output = "{} files would be deleted"
        # print(debug_output.format(len(all_removed_files)), *all_removed_files, sep='\n- ')
        print(debug_output.format(len(all_removed_files)))

    def delete_html_file(self, domain: str) -> list:
        removed_files = []

        if self.args.type == "calendars":
            current_dir = os.path.join(DATA_DIR_PATH, domain)
        elif self.args.type == "events":
            current_dir = os.path.join(DATA_DIR_PATH, domain, DownloadEvents.EVENTS_FOLDER_NAME)
        else:
            raise Exception("Unknown type!")

        if os.path.isdir(current_dir):
            files = sorted([file for file in os.listdir(current_dir) if file.endswith('.html')], key=str.lower)

            for filename in files:
                file_path = os.path.join(current_dir, filename)

                if os.path.isfile(file_path) and filename.startswith(self.args.timestamp):
                    if not self.args.dry_run:
                        os.remove(file_path)

                    removed_files.append(file_path)

        return removed_files


if __name__ == '__main__':
    delete_html_files = DeleteHTMLFiles()
    delete_html_files.run()
