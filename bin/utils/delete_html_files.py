import argparse
import os
from typing import List

from bin.download_events import DownloadEvents
from lib import utils
from lib.constants import DATA_DIR_PATH


class DeleteHTMLFiles:
    """ Deletes all the HTML files of the specified type and with a name prefix as the specified timestamp. """

    FILE_TYPES = ["calendars", "events"]

    def __init__(self):
        self.args = self._parse_arguments()

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('type', type=str, choices=DeleteHTMLFiles.FILE_TYPES,
                            help='delete HTML files of the specified content type')
        parser.add_argument('-file-name-prefix', type=str, required=True,
                            help="delete HTML files with the specified name prefix; "
                                 "timestamp can be as specific as needed "
                                 "- e.g. '2020-01-17', '2020-01-21_22-47-02'")
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store anything permanently")
        parser.add_argument('--domain', type=str, default=None,
                            help="delete HTML file of only the specified calendar domain")
        return parser.parse_args()

    def run(self) -> None:
        input_domains = self._load_input_domains()
        self._delete_html_files(input_domains)

    def _load_input_domains(self) -> List[str]:
        print("Loading input domains...")

        if self.args.domain:
            return [self.args.domain]
        return [base['domain'] for base in utils.load_base()]

    def _delete_html_files(self, domain_list: List[str]) -> None:
        print("Deleting files...")

        all_removed_files = []
        for domain in domain_list:
            domain_removed_files = self._delete_html_files_helper(domain)
            all_removed_files.extend(domain_removed_files)

        print(">> {} files{}deleted:".format(len(all_removed_files), " would be " if self.args.dry_run else " "))
        print(*all_removed_files, sep='\n')

    def _delete_html_files_helper(self, domain: str) -> List[str]:
        removed_files = []

        if self.args.type == "calendars":
            current_dir = os.path.join(DATA_DIR_PATH, domain)
        elif self.args.type == "events":
            current_dir = os.path.join(DATA_DIR_PATH, domain, DownloadEvents.EVENTS_FOLDER_NAME)
        else:
            raise Exception("Unknown type of file: {}!".format(self.args.type))

        if os.path.isdir(current_dir):
            files = sorted([file for file in os.listdir(current_dir) if file.endswith('.html')], key=str.lower)
            for filename in files:
                file_path = os.path.join(current_dir, filename)
                if os.path.isfile(file_path) and filename.startswith(self.args.file_name_prefix):
                    if not self.args.dry_run:
                        os.remove(file_path)
                    removed_files.append(file_path)

        return removed_files


if __name__ == '__main__':
    delete_html_files = DeleteHTMLFiles()
    delete_html_files.run()
