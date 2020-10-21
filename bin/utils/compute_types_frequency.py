import json
from collections import defaultdict

from lib import utils


class ComputeTypesFrequency:

    def __init__(self) -> None:
        self.connection = utils.create_connection()

        missing_views = utils.check_db_views(self.connection, ["event_data_view"])
        if len(missing_views) != 0:
            raise Exception("Missing views in the DB: {}".format(missing_views))

    def run(self) -> None:
        result_dict = self.get_type_counts()
        print(json.dumps(result_dict, indent=4, ensure_ascii=False))

    def get_type_counts(self) -> dict:
        query = '''
                SELECT event_data__types, calendar__url
                FROM event_data_view
                '''
        cursor = self.connection.execute(query)
        result_list = cursor.fetchall()
        base_dict = utils.get_base_dict_per_url()

        types_frequency = defaultdict(int)
        types_per_parser = defaultdict(set)
        for types_str, calendar_url in result_list:
            types_list = json.loads(types_str) if types_str else []
            parser = base_dict[calendar_url]['parser']

            for event_type in types_list:
                types_frequency[event_type] += 1
                types_per_parser[parser].add(event_type)

        return {
            'types_frequency': {key: value for key, value in
                                sorted(types_frequency.items(), key=lambda tpl: tpl[1], reverse=True)},
            'types_per_parser': {key: list(value) for key, value in types_per_parser.items()}
        }


if __name__ == '__main__':
    compute_types_frequency = ComputeTypesFrequency()
    compute_types_frequency.run()
