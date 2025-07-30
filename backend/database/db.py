#remedylabs\backend\database\db.py

import sqlite3
import os
import sys
from contextlib import closing # For closing connection in lifespan context

# --- START: Temporary sys.path adjustment for config import ---
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
# --- END: Temporary sys.path adjustment ---

from config import DATABASE_FILE # Assuming DATABASE_FILE is defined here

# Global connection and cursor (for init_db and direct use if needed, but get_db is preferred for FastAPI)
_conn = None
_cursor = None

def get_db():
    """
    FastAPI dependency to get a database connection.
    Manages connection lifecycle for each request.
    """
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db_connection():
    """
    Initializes the global database connection.
    To be called once at application startup.
    """
    global _conn, _cursor
    if _conn is None:
        db_dir = os.path.dirname(DATABASE_FILE)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        _conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON;")
        _cursor = _conn.cursor()
        print(f"Database connection established successfully at: {DATABASE_FILE}")
    else:
        print("Database connection already established.")

def close_db_connection():
    """
    Closes the global database connection.
    To be called once at application shutdown.
    """
    global _conn, _cursor
    if _conn:
        _conn.close()
        _conn = None
        _cursor = None
        print("Database connection closed.")

def get_global_db_connection():
    """
    Returns the globally managed database connection.
    Used by DBManager and init_db.py.
    """
    global _conn
    if _conn is None:
        init_db_connection() # Ensure connection is initialized if not already
    return _conn

def get_global_db_cursor():
    """
    Returns the globally managed database cursor.
    """
    global _cursor
    if _cursor is None:
        get_global_db_connection() # Ensure connection and cursor are initialized
    return _cursor