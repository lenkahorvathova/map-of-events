import csv

from lib import utils


class GeocodeLocation:
    MUNICIPALITIES_OF_CR_FILE = "resources/municipalities_cr.csv"

    def __init__(self) -> None:
        self.connection = utils.create_connection()

    def run(self) -> None:
        events_to_geocode = self.load_events()
        geocoded_gps = self.parse_out_municipalities(events_to_geocode)

    def load_events(self) -> list:
        query = '''SELECT title, perex, location
                   FROM event_data
                   WHERE gps IS NULL'''

        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def parse_out_municipalities(self, events_to_geocode: list):
        municipalities = self.get_municipalities_of_CR()

        matches = []
        unmatched = []
        for event in events_to_geocode:
            event_text = ", ".join(filter(None, event))

            if any(municipality in event_text for municipality in municipalities):
                matches.append(event_text)
            else:
                unmatched.append(event_text)

        print("Could be geocoded: {}/{}".format(len(matches), len(events_to_geocode)))
        print("matches: {:.200}".format(", ".join(matches)))
        print("unmatched: {:.200}".format(", ".join(unmatched)))

    def get_municipalities_of_CR(self) -> set:
        municips = set()

        with open(self.MUNICIPALITIES_OF_CR_FILE, 'r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')

            for row in csv_reader:
                just_municip = row[0]
                with_region = ", ".join(row)
                municips.update({just_municip, with_region})

        return municips


if __name__ == "__main__":
    geocode_location = GeocodeLocation()
    geocode_location.run()