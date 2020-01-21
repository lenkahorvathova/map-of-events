from lib import utils


class SetupDB:
    """ Sets up a database according to the specified schema. """

    SCHEMA_PATH = "resources/schema.sql"

    def __init__(self):
        self.connection = utils.create_connection()

    def run(self) -> None:
        with self.connection:
            self.connection.execute("PRAGMA foreign_keys = ON")

            with open(self.SCHEMA_PATH, 'r') as schema_file:
                for command in schema_file.read().split(";"):
                    self.connection.execute(command)

            self.connection.commit()


if __name__ == '__main__':
    setup_db = SetupDB()
    setup_db.run()