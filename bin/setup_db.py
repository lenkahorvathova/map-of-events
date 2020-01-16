from lib.utils import create_connection

SCHEMA_PATH = "resources/schema.sql"


def setup_db() -> None:
    """
    Sets up a database by a schema specified in SCHEMA_PATH.
    """

    connection = create_connection()
    connection.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH, 'r') as file:
        for command in file.read().split(";"):
            connection.execute(command)

        connection.commit()


if __name__ == '__main__':
    setup_db()
