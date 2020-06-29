import csv
import io
import os
import sys
import time

import requests
from lxml import etree

from lib.constants import MUNICIPALITIES_OF_CR_FILE


class AddDeclensionOfMunicipalities:
    MUNICIPALITIES_OF_CR_WITH_DECLENSION_FILE = "resources/municipalities_cr_with_declension.csv"
    MUNICIPALITIES_COUNT = 6253
    LOCATIVE_CASE_XPATH = u".//*[@id='content']/div/table/tr/td[contains(text(), '6. pád')]/following-sibling::td[@class='centrovane']/descendant-or-self::*[not(@name='sup')]/text()"

    def run(self) -> None:
        input_municipalities = self.read_csv_file()
        self.add_declension(input_municipalities)

    def read_csv_file(self) -> list:
        print("Loading input municipalities...")

        with open(MUNICIPALITIES_OF_CR_FILE, 'r') as csv_input_file:
            csv_reader = csv.reader(csv_input_file, delimiter=';')
            return [row for row in csv_reader]

    def add_declension(self, input_municipalities: list) -> None:
        already_parsed = set()
        if not os.path.exists(AddDeclensionOfMunicipalities.MUNICIPALITIES_OF_CR_WITH_DECLENSION_FILE):
            with open(AddDeclensionOfMunicipalities.MUNICIPALITIES_OF_CR_WITH_DECLENSION_FILE, 'w') as csv_output_file:
                csv_writer = csv.writer(csv_output_file, lineterminator='\n')
                row = input_municipalities[0]
                row.append("LOCATIVE")
                csv_writer.writerow(row)
        else:
            with open(AddDeclensionOfMunicipalities.MUNICIPALITIES_OF_CR_WITH_DECLENSION_FILE, 'r') as csv_output_file:
                csv_reader = csv.reader(csv_output_file)
                for row in csv_reader:
                    already_parsed.add(", ".join(row[:2]))

        nok = []
        nothing_found = []
        more_than_one_found = []
        multiwords = []

        # x = 0
        with open(AddDeclensionOfMunicipalities.MUNICIPALITIES_OF_CR_WITH_DECLENSION_FILE, 'a') as csv_output_file:
            csv_writer = csv.writer(csv_output_file, lineterminator='\n')

            for index, row in enumerate(input_municipalities[1:]):
                debug_output = "{}/{} | {}".format(index + 1, AddDeclensionOfMunicipalities.MUNICIPALITIES_COUNT,
                                                   row[0])

                if ", ".join(row[:2]) in already_parsed:
                    continue
                # else:
                #     if x == 1:
                #         sys.exit()
                #     x += 1

                municipality_split = row[0].split()
                if len(municipality_split) == 1:
                    url = "https://prirucka.ujc.cas.cz/?id={}".format(row[0])
                else:
                    url = "https://prirucka.ujc.cas.cz/?slovo={}".format("+".join(municipality_split))
                    multiwords.append(row[0])

                try:
                    response = requests.get(url, headers={
                        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36",
                    }, timeout=5)
                except Exception as e:
                    debug_output += " | RETRY LATER (Exception: {})".format(e)
                    input_municipalities.append(row)
                    time.sleep(1)
                    print(debug_output)
                    continue

                if response.status_code == 200:
                    html = response.text
                    dom = etree.parse(io.StringIO(html), etree.HTMLParser())
                    found_elements = dom.xpath(AddDeclensionOfMunicipalities.LOCATIVE_CASE_XPATH)

                    if 'server is overloaded' in html:
                        if "not to wait" in html:
                            requests.get(url + "&action=free", headers={
                                'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36",
                            })
                            input_municipalities.append(row)
                            debug_output += " | RETRY LATER (Server overloaded: Processing another request)"
                            time.sleep(1)
                            print(debug_output)
                            continue
                        else:
                            debug_output += " | RETRY LATER (Server overloaded: Too many processed requests)"
                            debug_output += "\n>> Script terminated"
                            print(debug_output)
                            self.print_temp_stats(nok, nothing_found, more_than_one_found, multiwords)
                            sys.exit()

                    debug_output += " | OK"
                    if len(found_elements) == 0:
                        nothing_found.append(row[0])
                        debug_output += " (nothing found)"
                    elif len(found_elements) > 1:
                        more_than_one_found.append(row[0])
                        debug_output += " (more than one declension found)"

                    already_parsed.add(", ".join(row[:2]))
                    row.append(",".join(found_elements))

                else:
                    nok.append(row[0])
                    debug_output += " | NOK (status code: {})".format(response.status_code)

                csv_writer.writerow(row)
                time.sleep(1)
                print(debug_output)

        self.print_temp_stats(nok, nothing_found, more_than_one_found, multiwords)

    def print_temp_stats(self, nok: list, nothing_found: list, more_than_one_found: list, multiwords: list) -> None:
        print(">> NOKs ({}): {}".format(len(nok), nok))
        print(">> nothing_found ({}): {}".format(len(nothing_found), nothing_found))
        print(">> more_than_one_found ({}): {}".format(len(more_than_one_found), more_than_one_found))
        print(">> multiwords ({}): {}".format(len(multiwords), multiwords))


if __name__ == "__main__":
    add_declension_of_municipalities = AddDeclensionOfMunicipalities()
    add_declension_of_municipalities.run()
