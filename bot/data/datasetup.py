import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            dabloons INTEGER DEFAULT 0,
            bio TEXT DEFAULT '',
            dm_notifications INTEGER DEFAULT 1,
            show_status INTEGER DEFAULT 1,
            show_dabloons INTEGER DEFAULT 1,
            daily_last TEXT DEFAULT '',
            weekly_last TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT '.',
            welcome_channel INTEGER DEFAULT 0,
            welcome_msg TEXT DEFAULT 'Welcome {user} to {server}!',
            level_channel INTEGER DEFAULT 0,
            level_msg TEXT DEFAULT '{user} just reached level {level}!'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_leveling (
            server_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            total_xp INTEGER DEFAULT 0,
            PRIMARY KEY (server_id, user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT DEFAULT 'No reason provided',
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("[DATABASE] All tables verified/created.")


if __name__ == '__main__':
    setup_database()
