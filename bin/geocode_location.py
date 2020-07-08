import csv
import multiprocessing
import re
from collections import defaultdict

from lib import utils
from lib.constants import MUNICIPALITIES_OF_CR_FILE


class GeocodeLocation:
    ONLINE_PATTERN = r'\b(online|Online|ONLINE|On-line|on-line|ON-LINE|Virtuálně|virtuálně)\b'

    def __init__(self) -> None:
        self.connection = utils.create_connection()

    def run(self) -> None:
        events_to_geocode = self.load_events()
        self.geocode_location(events_to_geocode)

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

    def geocode_location(self, events_to_geocode: list):
        matched_location = {
            "all": len(events_to_geocode),
            "no_match": 0,
            "no_match_no_gps": 0,
            "distinct_matches": 0,
            "distinct_matches_no_gps": 0,
            "more_than_one_matches": 0,
            "ambiguous_matches": 0,
            "online": 0,
            "events": defaultdict(dict)
        }

        input_tuples = []
        municipalities = self.load_municipalities_csv()
        calendars_with_default_gps = [base_dict["url"] for base_dict in utils.get_base_by("default_gps")]

        for index, event in enumerate(events_to_geocode):
            input_tuples.append((index + 1, len(events_to_geocode), event, municipalities, calendars_with_default_gps))

        with multiprocessing.Pool(32) as p:
            matched_location["events"] = p.map(GeocodeLocation.parse_out_municipalities, input_tuples)

        for match in matched_location["events"]:
            if len(match["matched"]) == 0:
                matched_location["no_match"] += 1
                if not match["has_default_gps"]:
                    matched_location["no_match_no_gps"] += 1
            elif len(match["matched"]) == 1:
                matched_location["distinct_matches"] += 1
                if not match["has_default_gps"]:
                    matched_location["distinct_matches_no_gps"] += 1
            elif len(match["matched"]) > 1:
                matched_location["more_than_one_matches"] += 1

            if len(match["ambiguous"]) > 0:
                matched_location["ambiguous_matches"] += 1

            if match["online"]:
                matched_location["online"] += 1

        utils.store_to_json_file(matched_location, "data/tmp/geocode_location_output.json")

    @staticmethod
    def load_municipalities_csv() -> list:
        print("Loading municipalities...")

        municipalities = []
        with open(MUNICIPALITIES_OF_CR_FILE, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            seen = set()
            ambiguous = set()

            for municip, district, locative, gps in csv_reader:
                locative_list = locative.split("; ")
                pattern_value_list = [municip] + locative_list + [municip.upper()] + [loc.upper() for loc in
                                                                                      locative_list]
                pattern_value = "|".join(pattern_value_list)

                municip_dict = {
                    "municipality": municip,
                    "district": district,
                    "re_pattern": re.compile(r'\b({})\b'.format(pattern_value))
                }
                municipalities.append(municip_dict)

                if municip in seen:
                    ambiguous.add(municip)
                seen.add(municip)

        for municip_dict in municipalities:
            if municip_dict["municipality"] in ambiguous:
                municip_dict["ambiguous"] = True
            else:
                municip_dict["ambiguous"] = False

        return municipalities

    @staticmethod
    def parse_out_municipalities(input_tuple: tuple) -> dict:
        input_index, total_length, event, municipalities, calendars_with_default_gps = input_tuple
        event_id, title, perex, location, calendar_url = event

        event_dict = {
            "id": event_id,
            "count": 0,
            "matched": set(),
            "ambiguous": set(),
            "online": False,
            "has_default_gps": calendar_url in calendars_with_default_gps,
            "title": title,
            "perex": perex,
            "location": location
        }

        priority_order = [location, title, perex]
        for text in priority_order:
            event_dict["online"] = GeocodeLocation.match_online_in_text(text)

            matches = GeocodeLocation.match_municipality_in_text(text, municipalities)
            for match_dict in matches:
                matched = "{}, {}".format(match_dict["municipality"], match_dict["district"])

                if not GeocodeLocation.is_ambiguous(text, match_dict):
                    event_dict["matched"].add(matched)
                else:
                    event_dict["ambiguous"].add(matched)

            if len(event_dict["matched"]) > 0:
                break

        event_dict["matched"] = list(event_dict["matched"])
        event_dict["ambiguous"] = list(event_dict["ambiguous"])

        print("{}/{} | Geocoding event: {}".format(input_index, total_length, event_id))

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
            if district_match:
                return False
            else:
                return True


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()
