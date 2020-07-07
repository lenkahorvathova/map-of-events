import argparse
import csv

from lxml import etree


class AddDeclensionOfMunicipalities:
    CUZK_XML_FILE_PATH = "resources/20200630_ST_UZSZ.xml"
    OUTPUT_CSV_FILE_PATH = "resources/municipalities_cr.csv"

    def __init__(self) -> None:
        self.args = self._parse_arguments()

        root = self.read_xml_file()
        self.ns = root.nsmap
        self.data = root.find("vf:Data", namespaces=self.ns)

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")

        return parser.parse_args()

    def run(self) -> None:
        districts = self.get_districts()
        municipalities_info = self.get_municipalities_info(districts)
        self.write_to_csv(municipalities_info, self.args.dry_run)

    @staticmethod
    def read_xml_file() -> etree.ElementTree:
        print("Loading input file...")

        tree = etree.parse(AddDeclensionOfMunicipalities.CUZK_XML_FILE_PATH)
        root = tree.getroot()

        return root

    def get_districts(self) -> dict:
        print("Loading districts...")

        districts = self.data.find("vf:Okresy", namespaces=self.ns)

        result_dict = {}
        for district in districts:
            code = district.find("oki:Kod", namespaces=self.ns).text
            name = district.find("oki:Nazev", namespaces=self.ns).text
            result_dict[code] = name

        return result_dict

    def get_municipalities_info(self, districts: dict) -> list:
        print("Loading municipality info...")

        municipalities = self.data.find("vf:Obce", namespaces=self.ns)

        result_list = []
        for municipality in municipalities:
            name = municipality.find("obi:Nazev", namespaces=self.ns).text
            district_code = municipality.find("obi:Okres/oki:Kod", namespaces=self.ns).text
            locative = municipality.find("obi:MluvnickeCharakteristiky/com:Pad6", namespaces=self.ns).text

            result_list.append((name, districts[district_code], locative))

        return result_list

    def write_to_csv(self, municipalities_info: list, dry_run: bool) -> None:
        header = ("MUNICIPALITY", "DISTRICT", "LOCATIVE OF MUNICIPALITY")

        if dry_run:
            print(">> Would be written into CSV file:")
            print(",".join(header))
            print("\n".join([",".join(el) for el in municipalities_info]))
        else:
            print("Writing to CSV file...")

            with open(AddDeclensionOfMunicipalities.OUTPUT_CSV_FILE_PATH, 'w') as csv_file:
                csv_writer = csv.writer(csv_file, lineterminator='\n')
                csv_writer.writerow(header)
                csv_writer.writerows(municipalities_info)


if __name__ == "__main__":
    add_declension_of_municipalities = AddDeclensionOfMunicipalities()
    add_declension_of_municipalities.run()
