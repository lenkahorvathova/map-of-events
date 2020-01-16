import sqlite3
from sqlite3 import Error

SCHEMA_PATH = "resources/schema.sql"


def create_connection(db_file: str) -> sqlite3.Connection:
    """
    Creates a SQLite3 Connection to the DB at db_file.

    :param db_file: a path to the database
    :return: SQLite3 Connection
    """

    connection = None

    try:
        connection = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return connection


def setup_db(connection: sqlite3.Connection) -> None:
    """
    Sets up a database schema specified in SCHEMA_PATH.

    :param connection: a created SQLite3 Connection
    """

    connection.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH, 'r') as file:
        for command in file.read().split(";"):
            connection.execute(command)

        connection.commit()
