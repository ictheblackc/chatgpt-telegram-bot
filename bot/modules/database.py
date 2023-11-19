import os
import logging
import sqlite3

from bot.config import Config as conf


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
            role VARCHAR,
            answer_1 VARCHAR,
            answer_2 VARCHAR,
            answer_3 VARCHAR,
            answer_4 VARCHAR
        );
        """
        cursor.execute(sql)
        connection.commit()
        sql = """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            key VARCHAR,
            value VARCHAR
        );
        """
        cursor.execute(sql)
        connection.commit()
        cursor.close()

    def connection(self):
        db_path = os.path.join(os.getcwd(), f'{self.name}.sqlite3')
        if not os.path.exists(db_path):
            self.create_db()
        return sqlite3.connect(f'{self.name}.sqlite3', check_same_thread=False)

    def insert_user(self, user_id, is_bot, first_name, last_name, username, language_code, is_premium, role):
        sql = f"""
        INSERT OR IGNORE INTO users (
            id,
            is_bot,
            first_name,
            last_name,
            username,
            language_code,
            is_premium,
            role
        ) VALUES (
            '{user_id}',
            '{is_bot}',
            '{first_name}',
            '{last_name}',
            '{username}',
            '{language_code}',
            '{is_premium}',
            '{role}'
        );
        """
        self._execute_query(sql)
        logging.info(f'User with id {user_id} added')

    def get_user(self, user_id):
        sql = f"""
        SELECT *
        FROM users
        WHERE id = '{user_id}';
        """
        result = self._execute_query(sql, True)
        return result[0]

    def update_user(self, user_id, key, value):
        sql = f"""
        UPDATE users
        SET {key} = '{value}'
        WHERE id = '{user_id}';
        """
        self._execute_query(sql)
        logging.info(f'User with id {user_id} updated')

    def get_settings_by_key(self, key):
        sql = f"""
        SELECT *
        FROM settings
        WHERE key = '{key}';
        """
        result = self._execute_query(sql, True)
        return result[0]

    def update_settings_by_key(self, key, value):
        sql = f"""
        UPDATE settings
        SET value = '{value}'
        WHERE key = '{key}';
        """
        self._execute_query(sql)
        logging.info(f'Settings with id {key} updated')

    def _execute_query(self, query, select=False):
        cursor = self._conn.cursor()
        cursor.execute(query)
        if select:
            result = cursor.fetchall()
            cursor.close()
            return result
        else:
            self._conn.commit()
        cursor.close()


database = Database(conf.DB_NAME)
