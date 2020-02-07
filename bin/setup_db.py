from lib import utils


class SetupDB:
    """ Sets up a database according to the schema. """

    SCHEMA_PATH = "resources/schema.sql"

    def __init__(self) -> None:
        self.connection = utils.create_connection()

    def run(self) -> None:
        self.connection.execute("PRAGMA foreign_keys = ON")

        with open(self.SCHEMA_PATH, 'r', encoding="utf-8") as schema_file:
            schema = schema_file.read().split(";")

            for command in schema:
                self.connection.execute(command)

        self.connection.commit()
        self.connection.close()


if __name__ == '__main__':
    setup_db = SetupDB()
    setup_db.run()
