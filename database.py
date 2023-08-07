import os
import logging
import sqlite3

import config


class Database:
    """Class for database work."""
    def __init__(self, name):
        self.name = name
        self._conn = self.connection()
        logging.info('Database connection established')

    def create_db(self):
        connection = sqlite3.connect(f'{self.name}.sqlite3')
        logging.info('Database created')
        cursor = connection.cursor()
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            is_bot INTEGER,
            first_name VARCHAR,
            last_name VARCHAR,
            username VARCHAR,
            language_code VARCHAR,
            is_premium INTEGER,
            answer_1 VARCHAR,
            answer_2 VARCHAR,
            answer_3 VARCHAR,
            answer_4 VARCHAR
        );
        """
        cursor.execute(sql)
        connection.commit()
        cursor.close()

    def connection(self):
        db_path = os.path.join(os.getcwd(), f'{self.name}.sqlite3')
        if not os.path.exists(db_path):
            self.create_db()
        return sqlite3.connect(f'{self.name}.sqlite3')


database = Database(config.DB_NAME)
