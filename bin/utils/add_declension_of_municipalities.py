import csv
import io

import requests
from lxml import etree

from lib.constants import MUNICIPALITIES_OF_CR_FILE


class AddDeclensionOfMunicipalities:
    LOCATIVE_CASE_XPATH = u".//*[@id='content']/div/table/tr/td[contains(text(), '6. pád')]/following-sibling::td[@class='centrovane']/descendant-or-self::*/text()"

    def run(self):
        nok = []
        nothing_found = []
        more_than_one_found = []
        multiwords = []

        with open(MUNICIPALITIES_OF_CR_FILE, 'r') as csv_input_file:
            csv_reader = csv.reader(csv_input_file, delimiter=';')

            with open("resources/municipalities_cr_with_declension.csv", 'a') as csv_output_file:
                csv_writer = csv.writer(csv_output_file, lineterminator='\n')

                row = next(csv_reader)
                row.append("LOCATIVE")
                csv_writer.writerow(row)

                for index, row in enumerate(csv_reader):
                    print(index + 1, "/ 6253")

                    municipality_split = row[0].split()
                    if len(municipality_split) == 1:
                        url = "https://prirucka.ujc.cas.cz/?id={}".format(row[0])
                    else:
                        url = "https://prirucka.ujc.cas.cz/?slovo={}".format("+".join(municipality_split))
                        multiwords.append(row[0])

                    response = requests.get(url, headers={
                        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36",
                    })

                    found_elements = []
                    if response.status_code == 200:
                        html = response.text
                        dom = etree.parse(io.StringIO(html), etree.HTMLParser())
                        found_elements = dom.xpath(AddDeclensionOfMunicipalities.LOCATIVE_CASE_XPATH)
                    else:
                        nok.append(row[0])

                    if len(found_elements) == 0:
                        nothing_found.append(row[0])

                    if len(found_elements) > 1:
                        more_than_one_found.append(row[0])

                    if found_elements:
                        row.append(", ".join(found_elements))

                    csv_writer.writerow(row)

        print(">> NOKs ({}): {}".format(len(nok), nok))
        print(">> nothing_found ({}): {}".format(len(nothing_found), nothing_found))
        print(">> more_than_one_found ({}): {}".format(len(more_than_one_found), more_than_one_found))
        print(">> multiwords ({}): {}".format(len(multiwords), multiwords))


if __name__ == "__main__":
    add_declension_of_municipalities = AddDeclensionOfMunicipalities()
    add_declension_of_municipalities.run()
