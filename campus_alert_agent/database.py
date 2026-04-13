"""Database operations for campus_alert_agent."""
import sqlite3
import logging

def init_db() -> None:
    """Initialize the SQLite database and create the table if it does not exist."""
    try:
        conn = sqlite3.connect("seen_alerts.db")
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_urls (
                    id INTEGER PRIMARY KEY,
                    url TEXT,
                    content_hash TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(url, content_hash)
                )
            ''')
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Error initializing DB: {e}")

def is_already_seen(url: str, content_hash: str) -> bool:
    """Check if a specific URL and content hash are already in the database."""
    try:
        conn = sqlite3.connect("seen_alerts.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM seen_urls WHERE url = ? AND content_hash = ?",
                (url, content_hash)
            )
            row = cursor.fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Error checking DB for seen alert: {e}")
        return False

def mark_as_seen(url: str, content_hash: str) -> None:
    """Mark a URL and content hash as seen by inserting into the database."""
    try:
        conn = sqlite3.connect("seen_alerts.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO seen_urls (url, content_hash) VALUES (?, ?)",
                (url, content_hash)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Error marking alert as seen in DB: {e}")
