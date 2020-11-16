import os
from collections import defaultdict
from typing import List

from lib import utils


class PrepareKeywordsList:
    """ Prepares JSON of keywords with their stems and variations from input CSV file.
    Prerequisite:
        Czech stemmer (https://research.variancia.com/czech_stemmer) was used for preparing keywords variations.
        For this script to work, czech_stemmer.py must be downloaded into folder 'data/tmp/keywords'.
    """

    KEYWORDS_INPUT_TXT_FILE_PATH = "resources/research/keywords.csv"
    KEYWORDS_TEMPORARY_DIR_PATH = "data/tmp/keywords/"
    KEYWORDS_TEMPORARY_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, 'keywords.txt')
    CZECH_STEMMER_SCRIPT_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "czech_stemmer.py")
    LIGHT_STEM_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "light.txt")
    AGGRESSIVE_STEM_FILE_PATH = os.path.join(KEYWORDS_TEMPORARY_DIR_PATH, "aggressive.txt")
    KEYWORDS_OUTPUT_JSON_FILE_PATH = "resources/event_keywords.json"

    def __init__(self) -> None:
        try:
            utils.check_file(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH)
        except Exception as e:
            raise Exception("Please, download a stemming script from '{}' to '{}'!".format(
                "https://research.variancia.com/czech_stemmer",
                PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH)) from e

    def run(self) -> None:
        self._prepare_input_keywords_file()
        self._stem_input_keywords()
        keywords_dict = self._prepare_keywords_dict()
        utils.store_to_json_file(keywords_dict, PrepareKeywordsList.KEYWORDS_OUTPUT_JSON_FILE_PATH)

    @staticmethod
    def _prepare_input_keywords_file() -> None:
        print("Preparing input keywords...")

        with open(PrepareKeywordsList.KEYWORDS_INPUT_TXT_FILE_PATH, 'r') as input_file:
            input_file.readline()  # header
            reader = input_file.read()

        data = reader.replace(',', ' , ').replace('|', ' | ')
        with open(PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH, 'w') as output_file:
            output_file.write(data)

    @staticmethod
    def _stem_input_keywords() -> None:
        print("Stemming keywords...")

        os.system("python3 {} light < {} > {}".format(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH,
                                                      PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH,
                                                      PrepareKeywordsList.LIGHT_STEM_FILE_PATH))
        os.system("python3 {} aggressive < {} > {}".format(PrepareKeywordsList.CZECH_STEMMER_SCRIPT_FILE_PATH,
                                                           PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH,
                                                           PrepareKeywordsList.AGGRESSIVE_STEM_FILE_PATH))

    def _prepare_keywords_dict(self) -> dict:
        print("Preparing resulting keywords...")

        result_dict = defaultdict(set)
        with open(PrepareKeywordsList.KEYWORDS_TEMPORARY_FILE_PATH) as keywords_file, \
                open(PrepareKeywordsList.LIGHT_STEM_FILE_PATH) as light_file, \
                open(PrepareKeywordsList.AGGRESSIVE_STEM_FILE_PATH) as aggressive_file:
            for keywords_line, light_stem_line, aggressive_stem_line in zip(keywords_file, light_file, aggressive_file):
                keyword, _, variations = keywords_line.partition(',')
                keyword = keyword.strip()
                variations = self._sanitize_list_values(variations.split('|'))

                light_keyword, _, light_variations = light_stem_line.partition(',')
                light_stem_list = [light_keyword.strip()]
                light_stem_list.extend(self._sanitize_list_values(light_variations.split('|')))

                aggressive_keyword, _, aggressive_variations = aggressive_stem_line.partition(',')
                aggressive_stem_list = [aggressive_keyword.strip()]
                aggressive_stem_list.extend(self._sanitize_list_values(aggressive_variations.split('|')))

                result_dict[keyword].update(variations)
                result_dict[keyword].update(light_stem_list)
                # result_dict[keyword].update(aggressive_stem_list)  # not including aggressive version

        return dict({key: sorted(list(value), key=str.lower)
                     for key, value in sorted(result_dict.items(), key=lambda tpl: tpl[0].lower())})

    @staticmethod
    def _sanitize_list_values(stemmed_words: List[str]) -> List[str]:
        stemmed_words = [word.strip() for word in stemmed_words]
        stemmed_words = filter(None, stemmed_words)
        return list(stemmed_words)


if __name__ == '__main__':
    prepare_keywords_list = PrepareKeywordsList()
    prepare_keywords_list.run()
