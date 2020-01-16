import sqlite3
from sqlite3 import Error

DATABASE_PATH = "data/map_of_events.db"


def create_connection() -> sqlite3.Connection:
    """
    Creates a SQLite3 Connection to the DB at DATABASE_PATH.

    :return: SQLite3 Connection
    """

    try:
        connection = sqlite3.connect(DATABASE_PATH)
        return connection

    except Error as error:
        print(error)
