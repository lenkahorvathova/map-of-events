import argparse
import csv
import json
import logging
import multiprocessing
import re
import sqlite3
from typing import List

from lib import utils, logger
from lib.arguments_parser import ArgumentsParser
from lib.constants import MUNICIPALITIES_OF_CR_FILE_PATH, SIMPLE_LOGGER_PREFIX


class GeocodeLocation:
    """ Geo-codes a location of parsed events without GPS. """

    ONLINE_REGEX = re.compile(r'\bonlin|Onlin|ONLIN|On-line|on-line|ON-LINE|Virtuáln|virtuáln\w*')
    OUTPUT_FILE_PATH = "data/tmp/geocode_location_output.json"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.logger = logger.set_up_script_logger(__file__, log_file=self.args.log_file, log_level=self.args.log_level)
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            utils.check_db_tables(self.connection,
                                  ["calendar", "event_url", "event_html", "event_data", "event_data_gps"])

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = ArgumentsParser()
        parser.set_description("Geo-codes a location of parsed events without GPS.")
        parser.add_argument('--events-ids', type=int, nargs="*",
                            help="geocode locations only of events with the specified event_data IDs")

        arguments = parser.parse_args()
        if arguments.events_ids and not arguments.dry_run:
            parser.error("--events-ids requires --dry-run")
        return arguments

    def run(self) -> None:
        input_events = self._load_input_events()
        municipalities = self._load_municipalities_csv()
        info_to_insert = self._geocode_locations(input_events, municipalities)
        self._get_stats(info_to_insert)
        self._store_to_db(info_to_insert, )
        self.connection.close()

    def _load_input_events(self) -> List[tuple]:
        self.logger.info("Loading input events...")

        query = '''
                    SELECT ed.id, ed.title, ed.perex, ed.location, ed.gps,
                           c.url
                    FROM event_data ed
                         INNER JOIN event_html eh ON ed.event_html_id = eh.id
                         INNER JOIN event_url eu ON eh.event_url_id = eu.id
                         INNER JOIN calendar c ON eu.calendar_id = c.id
                '''

        if self.args.events_ids:
            query += ''' AND ed.id IN ({})'''.format(",".join(["{}".format(event_id)
                                                               for event_id in self.args.events_ids]))
        else:
            query += ''' AND ed.id NOT IN (SELECT DISTINCT event_data_id FROM event_data_gps)'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def _load_municipalities_csv(self) -> List[dict]:
        self.logger.info("Loading czech municipalities...")

        municipalities = []
        with open(MUNICIPALITIES_OF_CR_FILE_PATH, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            seen = set()
            ambiguous = set()

            for municip, district, locative, gps in csv_reader:
                municip_list = [municip, municip.upper()]

                locative_list = []
                locative_split = locative.split("; ")
                locative_split = locative_split + [loc.upper() for loc in locative_split]
                for loc in locative_split:
                    for prep in ["v", "ve", "V", "VE"]:
                        locative_list.append(prep + " " + loc)

                municip_dict = {
                    "municipality": municip,
                    "district": district,
                    "gps": gps,
                    "ambiguous": False,
                    "re_pattern": re.compile(r'\b({})\b'.format("|".join(municip_list + locative_list)))
                }
                municipalities.append(municip_dict)

                if municip in seen:
                    ambiguous.add(municip)
                seen.add(municip)

        for municip_dict in municipalities:
            if municip_dict["municipality"] in ambiguous:
                municip_dict["ambiguous"] = True

        return municipalities

    def _geocode_locations(self, input_events: List[tuple], municipalities: List[dict]) -> List[dict]:
        self.logger.info("Geocoding events' locations...")

        logger.set_up_simple_logger(SIMPLE_LOGGER_PREFIX + __file__,
                                    log_file=self.args.log_file, log_level=self.args.log_level)
        calendars_with_default_gps = utils.get_base_dict_per_url(utils.get_base_with_default_gps())
        input_tuples = []
        for index, event in enumerate(input_events):
            input_tuples.append((index + 1, len(input_events), event, municipalities, calendars_with_default_gps))

        with multiprocessing.Pool(32) as p:
            return p.map(GeocodeLocation._geocode_locations_process, input_tuples)

    @staticmethod
    def _geocode_locations_process(input_tuple: (int, int, (int, str, str, str, str, str), List[dict], dict)) -> dict:
        simple_logger = logging.getLogger(SIMPLE_LOGGER_PREFIX + __file__)

        input_index, total_length, event, municipalities, calendars_with_default_gps = input_tuple
        event_id, title, perex, location, gps, calendar_url = event
        event_dict = {
            "id": event_id,
            "online": False,
            "has_gps": gps is not None,
            "has_default": calendar_url in calendars_with_default_gps,
            "base": calendars_with_default_gps[calendar_url] if calendar_url in calendars_with_default_gps else None,
            "geocoded_location": [],
            "matched": set(),
            "ambiguous": set(),
            "title": title,
            "perex": perex,
            "location": location
        }

        info_output = "{}/{} | Processing location of: {}".format(input_index, total_length, event_id)

        for text in [location, title]:
            event_dict["online"] = GeocodeLocation._match_online_in_text(text)
            if event_dict["online"]:
                break

        if not event_dict["has_gps"] and not event_dict["has_default"]:
            info_output += " | geocoding"
            priority_order = []
            last_location_index = -1
            if location:
                location_split = location.split(" ")
                for i in range(len(location_split) - 1, -1, -1):
                    joined_word = " ".join(location_split[i:])
                    priority_order.append(joined_word)
                    last_location_index += 1
            priority_order.extend([title, perex])

            for i in range(len(priority_order)):
                text = priority_order[i]
                matches = GeocodeLocation._match_municipality_in_text(text, municipalities)

                for match_dict in matches:
                    match_name = match_dict["municipality"] + ", " + match_dict["district"]
                    if GeocodeLocation._is_ambiguous(text, match_dict):
                        event_dict["ambiguous"].add(match_name)
                    else:
                        event_dict["matched"].add(match_name)
                        if match_dict not in event_dict["geocoded_location"]:
                            event_dict["geocoded_location"].append(match_dict)

                if i >= last_location_index and len(event_dict["matched"]) + len(event_dict["ambiguous"]) > 0:
                    break

        if len(event_dict["geocoded_location"]) == 0:
            event_dict["geocoded_location"] = None
        elif len(event_dict["geocoded_location"]) == 1:
            event_dict["geocoded_location"] = event_dict["geocoded_location"][0]
        elif len(event_dict["geocoded_location"]) > 1:
            longest_match = event_dict["geocoded_location"][0]
            for match in event_dict["geocoded_location"][1:]:
                if len(match["municipality"]) > len(longest_match["municipality"]):
                    longest_match = match
            longest_match_split = longest_match["municipality"].split(" ")
            if len(longest_match_split) > 1:
                event_dict["geocoded_location"] = longest_match
            elif not event_dict["geocoded_location"][0]["ambiguous"]:
                event_dict["geocoded_location"] = event_dict["geocoded_location"][0]
            else:
                event_dict["geocoded_location"] = None

        if event_dict["geocoded_location"]:
            event_dict["geocoded_location"] = {key: event_dict["geocoded_location"][key]
                                               for key in ["municipality", "district", "gps"]}

        event_dict["matched"] = list(event_dict["matched"])
        event_dict["ambiguous"] = list(event_dict["ambiguous"])

        if event_dict["has_gps"] or event_dict["has_default"] or event_dict["geocoded_location"]:
            simple_logger.info(info_output + " | OK")
        else:
            simple_logger.warning(info_output + " | NOK")

        return event_dict

    @staticmethod
    def _match_online_in_text(text: str) -> bool:
        if not text:
            return False
        if GeocodeLocation.ONLINE_REGEX.search(text):
            return True
        return False

    @staticmethod
    def _match_municipality_in_text(text: str, municipalities: List[dict]) -> List[dict]:
        if not text:
            return []
        result = []
        for municip_dict in municipalities:
            if municip_dict["re_pattern"].search(text):
                result.append(municip_dict)
        return result

    @staticmethod
    def _is_ambiguous(text: str, municip_dict: dict) -> bool:
        if municip_dict["ambiguous"]:
            if municip_dict["municipality"] == municip_dict["district"]:
                if len(re.findall(municip_dict["re_pattern"], text)) < 2:
                    return True
            else:
                if not re.search(r'\b({})\b'.format(municip_dict["district"]), text):
                    return True

        return False

    def _get_stats(self, info_to_insert: List[dict]) -> None:
        self.logger.info("Preparing statistics...")

        result_dict = {
            "all": len(info_to_insert),
            "-online": 0,
            "-without_gps": 0,
            "--without_default_gps": 0,
            "---geocoded": 0,
            "---no_match": 0,
            "---distinct_match": 0,
            "---ambiguous_match": 0,
            "---more_than_one_match": 0,
            "---results": []
        }
        without_default_online = 0

        for match in info_to_insert:
            if match["online"]:
                result_dict["-online"] += 1

            if not match["has_gps"]:
                result_dict["-without_gps"] += 1

                if not match["has_default"]:
                    result_dict["--without_default_gps"] += 1

            if not match["has_gps"] and not match["has_default"]:
                if match["online"]:
                    without_default_online += 1

                if match["geocoded_location"]:
                    result_dict["---geocoded"] += 1

                if len(match["matched"]) == 0:
                    if len(match["ambiguous"]) == 0:
                        result_dict["---no_match"] += 1
                    else:
                        result_dict["---ambiguous_match"] += 1
                else:
                    if len(match["ambiguous"]) == 0:
                        result_dict["---distinct_match"] += 1
                    else:
                        result_dict["---more_than_one_match"] += 1

                match_without_default = dict(match)
                del match_without_default["has_gps"]
                del match_without_default["has_default"]
                del match_without_default["base"]
                result_dict["---results"].append(match_without_default)

        if self.args.dry_run:
            print(json.dumps(result_dict, indent=4, ensure_ascii=False))
        else:
            utils.store_to_json_file(result_dict, GeocodeLocation.OUTPUT_FILE_PATH)
        self.logger.info(">> Online: {} / {}".format(result_dict["-online"], result_dict["all"]))
        self.logger.info(">> No GPS: {} / {}".format(result_dict["-without_gps"], result_dict["all"]))
        self.logger.info(">> No GPS and no default GPS: {} / {}".format(result_dict["--without_default_gps"],
                                                                        result_dict["-without_gps"]))
        without_default_not_online = result_dict["--without_default_gps"] - without_default_online
        self.logger.info(">> Successfully geocoded: {} / ({} + {})".format(result_dict["---geocoded"],
                                                                           without_default_not_online,
                                                                           without_default_online))

    def _store_to_db(self, info_to_insert: List[dict]) -> None:
        if not self.args.dry_run:
            self.logger.info("Inserting into DB...")

        geocoded = 0
        nok_list = set()
        data_to_insert = []
        for info in info_to_insert:
            event_id = info["id"]
            online = info["online"]
            has_gps = info["has_gps"]
            has_default = info["has_default"]
            gps = None
            location = None
            municipality = None
            district = None

            if not online:
                if has_default:
                    gps = info["base"]["default_gps"]
                    if "default_location" in info["base"]:
                        location = info["base"]["default_location"]
                elif info["geocoded_location"] is not None:
                    gps = info["geocoded_location"]["gps"]
                    municipality = info["geocoded_location"]["municipality"]
                    district = info["geocoded_location"]["district"]

            if not has_gps and not has_default:
                geocoded += 1

            if not has_gps and not has_default and not online and not municipality:
                nok_list.add(event_id)

            values = (online, has_default, gps, location, municipality, district, event_id)
            if self.args.dry_run:
                data_to_insert.append(values)
            else:
                query = '''
                            INSERT OR IGNORE INTO event_data_gps(online, has_default, gps, location, municipality, district, event_data_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        '''
                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    self.logger.error("Error occurred when inserting event '{}' into DB: {}".format(event_id, str(e)))
                    nok_list.add(event_id)
        if not self.args.dry_run:
            self.connection.commit()

        self.logger.debug(">> Data (online, has_default, gps, municipality, district, event_data_id):\n\t{}".format(
            "\n\t".join([str(tpl) for tpl in data_to_insert])))
        self.logger.info(">> Result: {} OKs + {} NOKs / {}".format(geocoded - len(nok_list), len(nok_list), geocoded))
        self.logger.info(">> Failed event_data IDs: {}".format(list(nok_list)))


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()
