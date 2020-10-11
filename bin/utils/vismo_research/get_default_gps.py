import argparse
import io
import json
import multiprocessing
import os
import re
import sys
import urllib.parse as urllib

import requests
from lxml import etree

from lib import utils
from lib.constants import VISMO_RESEARCH_DATA_DIR_PATH, INPUT_SITES_BASE_FILE_PATH


class GetDefaultGPS:
    """ Parses a location from the main page of a Vismo websites,
            geocodes GPS and updates the base file of input websites.

    Outputs a json file with statistics about location on Vismo websites.
    """

    OUTPUT_FILE_PATH = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "get_default_gps_output.json")
    GEOCODING_TEMPLATE_HTML_FILE = "resources/research/vismo_geocoding_template.html"
    GEOCODING_RESULT_HTML_FILE = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "geocoding_result.html")
    GEOCODING_OUTPUT_JSON_FILE = os.path.join(VISMO_RESEARCH_DATA_DIR_PATH, "geocoding_output.json")

    XPATH_CONTACT = '//address'
    XPATH_MAP = '//*[@id="mapka"]'

    SCRIPT_PARTS = ['1', '2', '3']

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.base = utils.get_active_base()

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--part', required=True, type=str, choices=GetDefaultGPS.SCRIPT_PARTS,
                            help='specifies a part of the scripts to be performed')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--domain', type=str, default=None,
                            help="get GPS only for the specified domain")

        return parser.parse_args()

    def run(self) -> None:
        if self.args.part == "1":
            input_domains = self.load_domains()
            found_info = self.get_addresses(input_domains)
            stats_output = self.compute_statistics(found_info)

            if self.args.dry_run:
                print(json.dumps(stats_output, indent=4))
            else:
                utils.store_to_json_file(stats_output, GetDefaultGPS.OUTPUT_FILE_PATH)
            self.geocode_address(found_info, self.args.dry_run)

        if self.args.part == "2":
            print("Manually perform following steps:\n"
                  "\t1. open '{}' in your browser;\n"
                  "\t2. right-click on the loaded site;\n"
                  "\t3. choose 'Inspect' option;\n"
                  "\t4. go to 'Console' tab;\n"
                  "\t5. wait until geocoding of addresses ends and json appears;\n"
                  "\t6. copy the resulting json into '{}'.".format(GetDefaultGPS.GEOCODING_RESULT_HTML_FILE,
                                                                   GetDefaultGPS.GEOCODING_OUTPUT_JSON_FILE))

        if self.args.part == "3":
            input_domains = self.load_domains()
            default_locations = self.get_default_locations()
            self.update_base(input_domains, default_locations, self.args.dry_run)

    def load_domains(self) -> list:
        if self.args.domain:
            website_base = utils.get_base_by_domain(self.args.domain)
            if website_base is None:
                sys.exit("Unknown domain '{}'!".format(self.args.domain))
            calendar_url = website_base.get('url', None)
            if calendar_url is None:
                sys.exit("Specified domain '{}' is no longer active!".format(self.args.domain))
            return [website_base]

        return self.base

    @staticmethod
    def get_addresses(input_domains: list) -> list:
        with multiprocessing.Pool(32) as p:
            return p.map(GetDefaultGPS.get_address, input_domains)

    @staticmethod
    def get_address(input_website: dict) -> dict:
        parsed_url = urllib.urlparse(input_website["url"])
        base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_url)

        debug_output = "Parsing URL: {}".format(base_url)
        result = {
            "domain": input_website["domain"],
            "base_url": base_url
        }

        try:
            r = requests.get(base_url, timeout=30)
            result["status_code"] = r.status_code

            if r.status_code == 200:
                dom = etree.parse(io.StringIO(r.text), etree.HTMLParser())

                contact = dom.xpath(GetDefaultGPS.XPATH_CONTACT)
                if contact:
                    result["contact"] = True
                    result["contact_value"] = [line.strip() for line in
                                               filter(lambda x: not x.isspace(), contact[0].itertext())]

                mapy_cz = dom.xpath(GetDefaultGPS.XPATH_MAP)
                if mapy_cz:
                    href_url = mapy_cz[0].get('href')
                    if not href_url:
                        element_a = mapy_cz[0].find('a')
                        if element_a is not None:
                            href_url = element_a.get('href')

                    if href_url:
                        response = requests.get(href_url)
                        parse_result = urllib.urlparse(response.url).query or urllib.urlparse(response.url).fragment
                        result_dict = dict(urllib.parse_qsl(parse_result))

                        if "continue" in result_dict:
                            redirect_parse_result = urllib.urlparse(result_dict["continue"])

                            if redirect_parse_result:
                                path = redirect_parse_result.path
                                matched_obj = re.search(r'@([^,]+),([^,]+)', path)

                                if matched_obj:
                                    redirected_value = {'lat': matched_obj.group(1), 'lon': matched_obj.group(2)}
                                    result["google_maps_redirected"] = True
                                    result["google_maps_redirected_value"] = redirected_value

                        if "!x" in result_dict:
                            result_dict['x'] = result_dict.pop("!x")
                        if "!/zakladni?x" in result_dict:
                            result_dict['x'] = result_dict.pop("!/zakladni?x")

                        keys = ('x', 'y')
                        mapy_cz_value = {key: result_dict[key] for key in keys if key in result_dict}

                        if mapy_cz_value:
                            mapy_cz_value['lat'] = mapy_cz_value.pop('y')
                            mapy_cz_value['lon'] = mapy_cz_value.pop('x')

                            result["mapy_cz"] = True
                            result["mapy_cz_value"] = mapy_cz_value

            debug_output += " ({})".format(r.status_code)

        except Exception as e:
            result["exception"] = str(e)
            debug_output += " (Exception)"

        print(debug_output)
        return result

    @staticmethod
    def compute_statistics(found_info: list) -> dict:
        output = {
            "statistics": {
                "all": len(found_info),
                "contact": 0,
                "map": 0,
                "mapy_cz": 0,
                # "mapy_cz_list": [],
                "google_maps_redirected": 0,
                # "google_maps_redirected_list": [],
                "none": 0,
                # "none_list": [],
                "exception": 0,
                # "exception_list": []
            },
            "location_info": found_info
        }

        stats = output["statistics"]

        for result in found_info:
            has_info = False
            if result.get("contact", False):
                has_info = True
                stats["contact"] += 1
            if result.get("mapy_cz", False):
                has_info = True
                stats["map"] += 1
                stats["mapy_cz"] += 1
                # stats["mapy_cz_list"].append(result["base_url"])
            if result.get("google_maps_redirected", False):
                has_info = True
                stats["map"] += 1
                stats["google_maps_redirected"] += 1
                # stats["google_maps_redirected_list"].append(result["base_url"])
            if not has_info:
                stats["none"] += 1
                # stats["none_list"].append(result["base_url"])
            if result.get("exception", False):
                stats["exception"] += 1
                # stats["exception_list"].append(result["base_url"])

        return output

    @staticmethod
    def geocode_address(found_info: list, dry_run: bool) -> None:
        output = {}
        regex = re.compile(r'[\n\r\t]')

        for input_website in found_info:
            if "contact_value" in input_website:
                contact_value = input_website["contact_value"]

                if contact_value and len(contact_value) >= 3:
                    address = "{} {}".format(contact_value[1], contact_value[2])
                    domain = input_website["domain"]
                    output[domain] = regex.sub(' ', address)

        if dry_run:
            print("Geocoding HTML file would be updated with this dataset: {}".format(json.dumps(output, indent=4)))
        else:
            with open(GetDefaultGPS.GEOCODING_TEMPLATE_HTML_FILE) as html_file:
                file = ''.join(html_file.readlines())
                file = file.replace('<<address_dataset>>', json.dumps(output, indent=4))

            with open(GetDefaultGPS.GEOCODING_RESULT_HTML_FILE, 'w') as f:
                f.write(file)

    @staticmethod
    def get_default_locations():
        with open(GetDefaultGPS.OUTPUT_FILE_PATH, 'r') as json_file:
            stats_dict = json.load(json_file)

        location_info = stats_dict["location_info"]
        default_locations = {}

        for municipality in location_info:
            if "contact_value" in municipality and len(municipality["contact_value"]) >= 1:
                domain = municipality["domain"]
                location = municipality["contact_value"][0]
                default_locations[domain] = location

        return default_locations

    @staticmethod
    def update_base(input_domains: list, default_locations: dict, dry_run: bool) -> None:
        with open(GetDefaultGPS.GEOCODING_OUTPUT_JSON_FILE) as json_file:
            dataset = json.load(json_file)
            found_gps = {}

            regex = re.compile(r'\(([^)]+)\)')
            for domain, address_array in dataset.items():
                if address_array:
                    address = address_array[0]
                    found_gps[domain] = regex.search(address).group(1)

        gps_count = 0
        without_gps = []
        for website in input_domains:
            domain = website["domain"]
            gps = found_gps.get(domain, None)
            if gps is not None:
                gps_count += 1
                website["default_gps"] = GetDefaultGPS.convert_gps_to_dec(gps)
                if domain in default_locations:
                    website["default_location"] = default_locations[domain]
            else:
                without_gps.append(website["domain"])

        if dry_run:
            print("Input base file would be updated with this dataset: {}".format(json.dumps(input_domains, indent=4)))
            print("Found GPS: {}/{}".format(gps_count, len(input_domains)))
            print("Websites left without GPS: {} ({})".format(len(without_gps), without_gps))
        else:
            utils.store_to_json_file(input_domains, INPUT_SITES_BASE_FILE_PATH)

            with open(GetDefaultGPS.OUTPUT_FILE_PATH) as file:
                stat_data = json.load(file)

            stat_data["geocoding_info"] = {
                "all_websites": len(input_domains),
                "websites_with_gps": gps_count,
                "websites_without_gps": len(without_gps),
                "websites_without_gps_list": without_gps
            }

            utils.store_to_json_file(stat_data, GetDefaultGPS.OUTPUT_FILE_PATH)

    @staticmethod
    def convert_gps_to_dec(gps: str) -> str:
        def convert_coord(dms_coord):
            direction = {'N': 1, 'S': -1, 'E': 1, 'W': -1}

            dec_coord = dms_coord.replace(u'°', ' ').replace('\'', ' ').replace('"', ' ')
            dec_coord = dec_coord.split()
            dec_coord_dir = dec_coord.pop()
            dec_coord.extend([0, 0, 0])
            dec_coord_num = int(dec_coord[0]) + int(dec_coord[1]) / 60.0 + float(dec_coord[2]) / 3600.0

            return dec_coord_num * direction[dec_coord_dir]

        lat_dms, lon_dms = gps.split(', ')
        lat_dec, lon_dec = convert_coord(lat_dms), convert_coord(lon_dms)

        return str(lat_dec) + ", " + str(lon_dec)


if __name__ == '__main__':
    get_default_gps = GetDefaultGPS()
    get_default_gps.run()
