import argparse
import json
import os
import shutil
from collections import defaultdict

from lib import utils


class PrepareKeywordsList:
    """
    Prerequisite:
        Czech stemmer (https://research.variancia.com/czech_stemmer) was used for preparing keywords variations.
        For this script to work, czech_stemmer.py must be downloaded into folder 'data/tmp/keywords'.
    """
    KEYWORDS_INPUT_TXT_FILE_PATH = "resources/research/keywords.txt"
    KEYWORDS_TEMPORARY_DIR_PATH = "data/tmp/keywords/"
    KEYWORDS_TEMPORARY_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, 'keywords.txt')
    CZECH_STEMMER_SCRIPT_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "czech_stemmer.py")
    LIGHT_STEM_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "light.txt")
    AGGRESSIVE_STEM_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "aggressive.txt")
    KEYWORDS_OUTPUT_JSON_FILE_PATH = "resources/event_keywords.json"

    def __init__(self) -> None:
        self.args = self._parse_arguments()

        if not os.path.isfile(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH):
            raise Exception("Script '{}' doesn't exist (you can download it from '{}')!".format(
                PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH,
                "https://research.variancia.com/czech_stemmer"))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")

        return parser.parse_args()

    def run(self) -> None:
        self._stem_input_keywords()
        keywords_dict = self._prepare_keywords_dict()
        if self.args.dry_run:
            print(json.dumps(keywords_dict, indent=4, ensure_ascii=False))
        else:
            utils.store_to_json_file(keywords_dict, PrepareKeywordsList.KEYWORDS_OUTPUT_JSON_FILE_PATH)

    @staticmethod
    def _stem_input_keywords() -> None:
        shutil.copy2(PrepareKeywordsList.KEYWORDS_INPUT_TXT_FILE_PATH, PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH)
        os.system("python3 {} light < {} > {}".format(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH,
                                                      PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH,
                                                      PrepareKeywordsList.LIGHT_STEM_FILE_PATH))
        os.system("python3 {} aggressive < {} > {}".format(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH,
                                                           PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH,
                                                           PrepareKeywordsList.AGGRESSIVE_STEM_FILE_PATH))

    def _prepare_keywords_dict(self) -> dict:
        result_dict = defaultdict(set)

        with open(PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH) as keywords_file, \
                open(PrepareKeywordsList.LIGHT_STEM_FILE_PATH) as light_file, \
                open(PrepareKeywordsList.AGGRESSIVE_STEM_FILE_PATH) as aggressive_file:
            for keywords_line, light_stem_line, aggressive_stem_line in zip(keywords_file, light_file, aggressive_file):
                keywords_split = self._strip_list_values(keywords_line.split(" "))
                light_split = self._strip_list_values(light_stem_line.split(" "))
                aggressive_split = self._strip_list_values(aggressive_stem_line.split(" "))

                keyword = keywords_split[0]
                variations = keywords_split[1:]
                result_dict[keyword].update(variations)
                result_dict[keyword].update(light_split)
                # result_dict[keyword].update(aggressive_split)  # not including aggressive version

        return dict({key: sorted(list(value)) for key, value in sorted(result_dict.items())})

    @staticmethod
    def _strip_list_values(stemmed_words: list) -> list:
        return [word.strip() for word in stemmed_words]


if __name__ == '__main__':
    prepare_keywords_list = PrepareKeywordsList()
    prepare_keywords_list.run()
