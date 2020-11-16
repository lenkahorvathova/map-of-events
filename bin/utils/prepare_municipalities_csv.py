import csv
import math
import time
from typing import List

import requests
from lxml import etree

from lib.constants import MUNICIPALITIES_OF_CR_FILE_PATH


class PrepareMunicipalitiesCSV:
    """ Prepares a CSV file with inflected municipalities and their GPS coordinates from RUIAN data. """

    CUZK_XML_FILE_PATH = "resources/geocoding/20200630_ST_UZSZ.xml"

    SOURCE_EPSG = 5514  # Czechia
    TARGET_EPSG = 4326  # World

    def __init__(self) -> None:
        root = self._read_xml_file()
        self.ns = root.nsmap
        self.data = root.find("vf:Data", namespaces=self.ns)

    def run(self) -> None:
        districts = self._get_districts()
        municipalities_info = self._get_municipalities_info(districts)
        converted_info = self._convert_gml_pos_to_gps(municipalities_info)
        self._write_to_csv(converted_info)

    @staticmethod
    def _read_xml_file() -> etree.ElementTree:
        print("Loading input file...")

        tree = etree.parse(PrepareMunicipalitiesCSV.CUZK_XML_FILE_PATH)
        root = tree.getroot()
        return root

    def _get_districts(self) -> dict:
        print("Loading districts...")

        districts = self.data.find("vf:Okresy", namespaces=self.ns)
        result_dict = {}
        for district in districts:
            code = district.find("oki:Kod", namespaces=self.ns).text
            name = district.find("oki:Nazev", namespaces=self.ns).text
            result_dict[code] = name
        return result_dict

    def _get_municipalities_info(self, districts: dict) -> List[tuple]:
        print("Loading municipalities' info...")

        municipalities = self.data.find("vf:Obce", namespaces=self.ns)
        result_list = []
        for municipality in municipalities:
            name = municipality.find("obi:Nazev", namespaces=self.ns).text
            district_code = municipality.find("obi:Okres/oki:Kod", namespaces=self.ns).text
            locative = municipality.find("obi:MluvnickeCharakteristiky/com:Pad6", namespaces=self.ns).text

            gml_position_path = "obi:Geometrie/obi:DefinicniBod/gml:MultiPoint/gml:pointMembers/gml:Point/gml:pos"
            gml_position = municipality.find(gml_position_path, namespaces=self.ns).text

            result_list.append((name, districts[district_code], locative, gml_position))

        return result_list

    def _convert_gml_pos_to_gps(self, municipalities_info: List[tuple]) -> List[tuple]:
        print("Converting to GPS...")

        batch_size = 100
        converted_list = []
        for i in range(0, len(municipalities_info), batch_size):
            curr_batch = municipalities_info[i:i + batch_size]
            curr_batch_gml_pos = [",".join(m[-1].split(" ")) for m in curr_batch]
            url = "http://epsg.io/trans?data={}&s_srs={}&&t_srs={}".format(";".join(curr_batch_gml_pos),
                                                                           self.SOURCE_EPSG, self.TARGET_EPSG)
            response = requests.get(url)
            response_json = response.json()
            for j in range(len(curr_batch)):
                gps = "{},{}".format(str(response_json[j]["y"]), str(response_json[j]["x"]))
                new_tuple = municipalities_info[i + j][:-1] + (gps,)
                converted_list.append(new_tuple)

            time.sleep(3)
            print("...{}/{} batches processed".format((i // batch_size) + 1,
                                                      math.ceil(len(municipalities_info) / batch_size)))
        return converted_list

    @staticmethod
    def _write_to_csv(converted_info: List[tuple]) -> None:
        print("Writing to output CSV file...")

        header = ("MUNICIPALITY", "DISTRICT", "LOCATIVE OF MUNICIPALITY", "GPS")
        converted_info.sort()
        with open(MUNICIPALITIES_OF_CR_FILE_PATH, 'w') as csv_file:
            csv_writer = csv.writer(csv_file, lineterminator='\n')
            csv_writer.writerow(header)
            csv_writer.writerows(converted_info)


if __name__ == "__main__":
    prepare_municipalities_csv = PrepareMunicipalitiesCSV()
    prepare_municipalities_csv.run()
