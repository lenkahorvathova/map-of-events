import csv
import multiprocessing
import re

from lib import utils
from lib.constants import MUNICIPALITIES_OF_CR_FILE


class GeocodeLocation:
    ONLINE_PATTERN = r'\b(online|Online|ONLINE|On-line|on-line|ON-LINE|Virtuálně|virtuálně)\b'
    OUTPUT_FILE_PATH = "data/tmp/geocode_location_output.json"

    def __init__(self) -> None:
        self.connection = utils.create_connection()

    def run(self) -> None:
        events_to_geocode = self.load_events()
        municipalities = self.load_municipalities_csv()
        info_to_insert = self.geocode_events(events_to_geocode, municipalities)
        # self.store_to_db(info_to_insert, self.args.dry_run)

    def load_events(self) -> list:
        print("Loading events...")

        query = '''SELECT ed.id, ed.title, ed.perex, ed.location, c.url
                   FROM event_data ed 
                   JOIN event_html eh ON ed.event_html_id = eh.id
                   JOIN event_url eu ON eh.event_url_id = eu.id
                   JOIN calendar c ON eu.calendar_id = c.id
                   WHERE ed.gps IS NULL'''

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

    def geocode_events(self, events_to_geocode: list, municipalities: list) -> list:
        result_dict = {
            "all": len(events_to_geocode),
            "-online": 0,
            "without_default_gps": 0,
            "-geocoded": 0,
            "-no_match": 0,
            "-distinct_matches": 0,
            "-more_than_one_matches": 0,
            "-ambiguous_matches": 0,
            "-geocoded_events": []
        }

        input_tuples = []
        calendars_with_default_gps = [base_dict["url"] for base_dict in utils.get_base_by("default_gps")]
        for index, event in enumerate(events_to_geocode):
            input_tuples.append((index + 1, len(events_to_geocode), event, municipalities, calendars_with_default_gps))

        with multiprocessing.Pool(32) as p:
            result_info = p.map(GeocodeLocation.parse_out_municipalities, input_tuples)

        for match in result_info:
            if match["online"]:
                result_dict["-online"] += 1

            if not match["has_default"]:
                result_dict["without_default_gps"] += 1

                if match["geocoded_location"]:
                    result_dict["-geocoded"] += 1
                else:
                    match["geocoded_location"] = None

                if len(match["matched"]) == 0:
                    result_dict["-no_match"] += 1
                elif len(match["matched"]) == 1:
                    result_dict["-distinct_matches"] += 1
                elif len(match["matched"]) > 1:
                    result_dict["-more_than_one_matches"] += 1

                if len(match["ambiguous"]) > 0:
                    result_dict["-ambiguous_matches"] += 1

                del match["has_default"]
                result_dict["-geocoded_events"].append(match)

        # if not self.args.dry_run:
        utils.store_to_json_file(result_dict, GeocodeLocation.OUTPUT_FILE_PATH)

        return result_info

    @staticmethod
    def parse_out_municipalities(input_tuple: tuple) -> dict:
        input_index, total_length, event, municipalities, calendars_with_default_gps = input_tuple
        event_id, title, perex, location, calendar_url = event

        event_dict = {
            "id": event_id,
            "online": False,
            "has_default": calendar_url in calendars_with_default_gps,
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

        priority_order = []
        if location:
            location_split = location.split(" ")
            for i in range(len(location_split) - 1, -1, -1):
                joined_word = " ".join(location_split[i:])
                priority_order.append(joined_word)
        priority_order.extend([title, perex])

        for text in priority_order:
            event_dict["online"] = GeocodeLocation.match_online_in_text(text)

            if not event_dict["has_default"]:
                matches = GeocodeLocation.match_municipality_in_text(text, municipalities)
                for match_dict in matches:
                    match_name = match_dict["municipality"] + ", " + match_dict["district"]
                    if GeocodeLocation.is_ambiguous(text, match_dict):
                        event_dict["ambiguous"].add(match_name)
                    else:
                        event_dict["matched"].add(match_name)
                        event_dict["geocoded_location"].append({key: match_dict[key]
                                                                for key in ["municipality", "district", "gps"]})

            if event_dict["online"] or len(event_dict["matched"]) > 0:
                break

        if len(event_dict["geocoded_location"]) == 1:
            event_dict["geocoded_location"] = event_dict["geocoded_location"][0]
        elif len(event_dict["geocoded_location"]) > 1:
            longest_match = event_dict["geocoded_location"][0]
            for match in event_dict["geocoded_location"][1:]:
                if len(match["municipality"]) > len(longest_match["municipality"]):
                    longest_match = match
            event_dict["geocoded_location"] = longest_match

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
            district_match = re.search(r'\b({})\b'.format(municip_dict["district"]), text)
            if not district_match:
                return True
        return False


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()
