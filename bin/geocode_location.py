import csv
import multiprocessing
import re
from collections import defaultdict

from lib import utils
from lib.constants import MUNICIPALITIES_OF_CR_FILE


class GeocodeLocation:
    def __init__(self) -> None:
        self.connection = utils.create_connection()

    def run(self) -> None:
        events_to_geocode = self.load_events()
        self.geocode_location(events_to_geocode)

    def load_events(self) -> list:
        query = '''SELECT id, title, perex, location
                   FROM event_data
                   WHERE gps IS NULL'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def geocode_location(self, events_to_geocode: list):
        print("Loading events...")
        matched_location = {
            "all": len(events_to_geocode),
            "matched": 0,
            "count": defaultdict(int),
            "events": defaultdict(dict)
        }

        input_tuples = []
        municipalities = self.get_municipalities_of_CR()
        for index, event in enumerate(events_to_geocode):
            input_tuples.append((index + 1, len(events_to_geocode), event, municipalities))

        with multiprocessing.Pool(32) as p:
            matched_location["events"] = p.map(GeocodeLocation.parse_out_municipalities, input_tuples)

        for match in matched_location["events"]:
            if match["count"] > 0:
                matched_location["count"][match["count"]] += 1

        matched_location["matched"] = sum(count for count in matched_location["count"].values())

        utils.store_to_json_file(matched_location, "data/tmp/geocode_location_output.json")
        print("Could be geocoded: {}/{}".format(matched_location["matched"], len(events_to_geocode)))

    @staticmethod
    def parse_out_municipalities(input_tuple: tuple) -> dict:
        input_index, total_length, event, municipalities = input_tuple
        id, title, perex, location = event

        event_dict = {
            "id": id,
            "count": 0,
            "matched": set(),
            "title": title,
            "perex": perex,
            "location": location
        }

        for municipality, pattern in municipalities.items():
            for key in ["title", "perex", "location"]:
                if event_dict[key]:
                    match = pattern.search(event_dict[key].lower())

                    if match:
                        event_dict["matched"].add(municipality)

        event_dict["matched"] = list(event_dict["matched"])
        event_dict["count"] = len(event_dict["matched"])

        print("{}/{} | Geocoding event: {}".format(input_index, total_length, id))

        return event_dict

    def get_municipalities_of_CR(self) -> dict:
        municips = {}

        with open(MUNICIPALITIES_OF_CR_FILE, 'r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')

        ambiguous = set()
        count_all = 0

        for row in csv_reader:
            count_all += 1

            if row[0] not in municips:
                municips[row[0]] = re.compile(r'\b({})\b'.format(row[0].lower()))
            else:
                ambiguous.add(row[0])

        print("Ambiguous municipalities: {}/{}".format(len(ambiguous), count_all))
        return municips


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()
