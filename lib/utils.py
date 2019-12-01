import sqlite3
from sqlite3 import Error


def create_connection(db_file: str) -> sqlite3.Connection:
    connection = None

    try:
        connection = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return connection


def setup_db(connection: sqlite3.Connection):
    connection.execute("pragma foreign_keys = on")

    with open("resources/schema.sql", 'r') as file:
        for command in file.read().split(";"):
            connection.execute(command)

        connection.commit()
