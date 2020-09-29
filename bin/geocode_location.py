import argparse
import csv
import json
import multiprocessing
import re
import sqlite3
import sys

from lib import utils
from lib.constants import MUNICIPALITIES_OF_CR_FILE


class GeocodeLocation:
    ONLINE_PATTERN = r'\b(online|Online|ONLINE|On-line|on-line|ON-LINE|Virtuálně|virtuálně)\b'
    OUTPUT_FILE_PATH = "data/tmp/geocode_location_output_2.json"

    def __init__(self) -> None:
        self.args = self._parse_arguments()
        self.connection = utils.create_connection()

        if not self.args.dry_run:
            missing_tables = utils.check_db_tables(self.connection,
                                                   ["calendar", "event_url", "event_html", "event_data",
                                                    "event_data_gps"])
            if len(missing_tables) != 0:
                raise Exception("Missing tables in the DB: {}".format(missing_tables))

    @staticmethod
    def _parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--dry-run', required='--events-ids' in sys.argv, action='store_true', default=False,
                            help="don't store any output and print to stdout")
        parser.add_argument('--events-ids', type=int, nargs="*",
                            help="geocode locations only of the specified events' IDs (possible only in 'dry-run' mode)")

        return parser.parse_args()

    def run(self) -> None:
        events_to_geocode = self.load_events()
        municipalities = self.load_municipalities_csv()
        info_to_insert = self.geocode_events(events_to_geocode, municipalities)
        self.get_stats(info_to_insert, self.args.dry_run)
        self.store_to_db(info_to_insert, self.args.dry_run)
        self.connection.close()

    def load_events(self) -> list:
        print("Loading events...")

        query = '''
                    SELECT ed.id, ed.title, ed.perex, ed.location, 
                           c.url
                    FROM event_data ed
                         INNER JOIN event_html eh ON ed.event_html_id = eh.id
                         INNER JOIN event_url eu ON eh.event_url_id = eu.id
                         INNER JOIN calendar c ON eu.calendar_id = c.id
                    WHERE ed.gps IS NULL
                '''

        if self.args.events_ids:
            query += ''' AND ed.id IN ({})'''.format(",".join(["{}".format(event_id)
                                                               for event_id in self.args.events_ids]))
        else:
            query += ''' AND ed.id NOT IN (SELECT DISTINCT event_data_id FROM event_data_gps)'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    @staticmethod
    def load_municipalities_csv() -> list:
        print("Loading municipalities...")

        municipalities = []
        with open(MUNICIPALITIES_OF_CR_FILE, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            seen = set()
            ambiguous = set()

            for municip, district, locative, gps in csv_reader:
                municip_list = [municip, municip.upper()]

                locative_list = []
                prepositions = ["v", "ve", "V", "VE"]
                locative_split = locative.split("; ")
                locative_split = locative_split + [loc.upper() for loc in locative_split]
                for loc in locative_split:
                    for prep in prepositions:
                        locative_list.append(prep + " " + loc)

                pattern_value = "|".join(municip_list + locative_list)

                municip_dict = {
                    "municipality": municip,
                    "district": district,
                    "gps": gps,
                    "ambiguous": False,
                    "re_pattern": re.compile(r'\b({})\b'.format(pattern_value))
                }
                municipalities.append(municip_dict)

                if municip in seen:
                    ambiguous.add(municip)
                seen.add(municip)

        for municip_dict in municipalities:
            if municip_dict["municipality"] in ambiguous:
                municip_dict["ambiguous"] = True

        return municipalities

    @staticmethod
    def geocode_events(events_to_geocode: list, municipalities: list) -> list:
        input_tuples = []
        calendars_with_default_gps = {base_dict["url"]: base_dict for base_dict in utils.get_base_with_default_gps()}

        for index, event in enumerate(events_to_geocode):
            input_tuples.append((index + 1, len(events_to_geocode), event, municipalities, calendars_with_default_gps))

        with multiprocessing.Pool(32) as p:
            return p.map(GeocodeLocation.geocode_event, input_tuples)

    @staticmethod
    def geocode_event(input_tuple: tuple) -> dict:
        input_index, total_length, event, municipalities, calendars_with_default_gps = input_tuple
        event_id, title, perex, location, calendar_url = event

        event_dict = {
            "id": event_id,
            "online": False,
            "has_default": calendar_url in calendars_with_default_gps,
            "base": calendars_with_default_gps[calendar_url] if calendar_url in calendars_with_default_gps else None,
            "geocoded_location": [],
            "matched": set(),
            "ambiguous": set(),
            "title": title,
            "perex": perex,
            "location": location
        }

        debug_output = "{}/{} | Processing event: {}".format(input_index, total_length, event_id)
        if not event_dict["has_default"]:
            debug_output += " - Geocoding..."
        print(debug_output)

        for text in [location, title]:
            event_dict["online"] = GeocodeLocation.match_online_in_text(text)
            if event_dict["online"]:
                break

        if not event_dict["has_default"]:
            priority_order = []

            last_location_index = -1
            if location:  # search for a municip. in location from right to left
                location_split = location.split(" ")
                for i in range(len(location_split) - 1, -1, -1):
                    joined_word = " ".join(location_split[i:])
                    priority_order.append(joined_word)
                    last_location_index += 1

            priority_order.extend([title, perex])

            for i in range(len(priority_order)):
                text = priority_order[i]
                matches = GeocodeLocation.match_municipality_in_text(text, municipalities)

                for match_dict in matches:
                    match_name = match_dict["municipality"] + ", " + match_dict["district"]

                    if GeocodeLocation.is_ambiguous(text, match_dict):
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

        return event_dict

    @staticmethod
    def match_online_in_text(text: str) -> bool:
        if not text:
            return False

        online_match = re.search(GeocodeLocation.ONLINE_PATTERN, text)
        if online_match:
            return True

        return False

    @staticmethod
    def match_municipality_in_text(text: str, municipalities: list) -> list:
        if not text:
            return []

        result = []
        for municip_dict in municipalities:
            municip_match = municip_dict["re_pattern"].search(text)
            if municip_match:
                result.append(municip_dict)

        return result

    @staticmethod
    def is_ambiguous(text: str, municip_dict: dict) -> bool:
        if municip_dict["ambiguous"]:
            if municip_dict["municipality"] == municip_dict["district"]:
                district_match = re.findall(municip_dict["re_pattern"], text)
                if len(district_match) < 2:
                    return True
            else:
                district_match = re.search(r'\b({})\b'.format(municip_dict["district"]), text)
                if not district_match:
                    return True

        return False

    @staticmethod
    def get_stats(info_to_insert: list, dry_run: bool) -> None:
        result_dict = {
            "all": len(info_to_insert),
            "-online": 0,
            "without_default_gps": 0,
            "-geocoded": 0,
            "-no_match": 0,
            "-distinct_match": 0,
            "-ambiguous_match": 0,
            "-more_than_one_match": 0,
            "-results": []
        }
        without_default_online = 0

        for match in info_to_insert:
            if match["online"]:
                result_dict["-online"] += 1

            if not match["has_default"]:
                result_dict["without_default_gps"] += 1

                if match["online"]:
                    without_default_online += 1

                if match["geocoded_location"]:
                    result_dict["-geocoded"] += 1

                if len(match["matched"]) == 0:
                    if len(match["ambiguous"]) == 0:
                        result_dict["-no_match"] += 1
                    else:
                        result_dict["-ambiguous_match"] += 1
                else:
                    if len(match["ambiguous"]) == 0:
                        result_dict["-distinct_match"] += 1
                    else:
                        result_dict["-more_than_one_match"] += 1

                match_without_default = dict(match)
                del match_without_default["has_default"]
                del match_without_default["base"]
                result_dict["-results"].append(match_without_default)

        debug_output = ""
        if dry_run:
            debug_output += ">> Would be stored into an output file:\n"
            debug_output += json.dumps(result_dict, indent=4, ensure_ascii=False)
        else:
            utils.store_to_json_file(result_dict, GeocodeLocation.OUTPUT_FILE_PATH)
            debug_output += ">> Online: {} / {}\n".format(result_dict["-online"], result_dict["all"])
            debug_output += ">> Without default GPS: {} / {}\n".format(result_dict["without_default_gps"],
                                                                       result_dict["all"])
            debug_output += ">> Successfully geocoded: {} / {} + {}".format(result_dict["-geocoded"], result_dict[
                "without_default_gps"] - without_default_online, without_default_online)

        print(debug_output)

    def store_to_db(self, info_to_insert: list, dry_run: bool) -> None:
        if not dry_run:
            print("Inserting geocoded locations into DB...")

        nok_list = set()
        data_to_insert = []

        for info in info_to_insert:
            event_id = info["id"]
            online = info["online"]
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
                elif info["geocoded_location"]:
                    gps = info["geocoded_location"]["gps"]
                    municipality = info["geocoded_location"]["municipality"]
                    district = info["geocoded_location"]["district"]

            if not online and not has_default and not municipality:
                nok_list.add(event_id)

            values = (online, has_default, gps, location, municipality, district, event_id)
            if dry_run:
                data_to_insert.append(values)
            else:
                query = '''
                            INSERT INTO event_data_gps(online, has_default, gps, location, municipality, district, event_data_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        '''

                try:
                    self.connection.execute(query, values)
                except sqlite3.Error as e:
                    print("Error occurred when inserting event '{}' into DB: {}".format(event_id, str(e)))
                    nok_list.add(event_id)

        self.connection.commit()

        debug_output = ""
        if dry_run:
            debug_output += ">> Data (online, has_default, gps, municipality, district, event_data_id):\n"
            debug_output += "\t{}\n".format("\n\t".join([str(tpl) for tpl in data_to_insert]))

        ok = len(info_to_insert) - len(nok_list)
        debug_output += ">> Result: {} OKs + {} NOKs / {}\n".format(ok, len(nok_list), len(info_to_insert))
        debug_output += ">> Failed event_data IDs: {}\n".format(list(nok_list))

        print(debug_output, end="")


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()
