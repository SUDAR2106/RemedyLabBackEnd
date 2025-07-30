#remedylabs/backend/database/db_utils.py

import sqlite3
from typing import Any, List, Dict, Optional, Tuple
import logging
# Import the global connection getter from db.py
from database.db import get_global_db_connection
logger = logging.getLogger(__name__)

class DBManager:
    """
    Manages database operations using a globally provided SQLite connection.
    """
    def __init__(self):
        try:
            self._conn = get_global_db_connection() # Use the global connection
            if self._conn is None:
                raise ValueError("Global database connection is None")
            
            # Verify it's actually a database connection
            if not hasattr(self._conn, 'cursor'):
                raise TypeError(f"Expected sqlite3.Connection, got {type(self._conn)}: {self._conn}")
            
            self._cursor = self._conn.cursor()
            logger.debug(f"DBManager initialized successfully with connection: {type(self._conn)}")
                
        except Exception as e:
            logger.error(f"Failed to initialize DBManager: {e}")
            logger.error(f"get_global_db_connection() returned: {type(get_global_db_connection())}")
            raise

    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetches one row from the database."""
        try:
            self._cursor.execute(query, params or ())
            row = self._cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error in fetch_one with query '{query}' and params {params}: {e}")
            raise

    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetches all rows from the database."""
        try:
            self._cursor.execute(query, params or ())
            rows = self._cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error in fetch_all with query '{query}' and params {params}: {e}")
            raise

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> bool:
        """Executes a query (INSERT, UPDATE, DELETE) and returns success status."""
        try:
            self._cursor.execute(query, params or ())
            self._conn.commit()
            logger.debug(f"Successfully executed query: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error executing query '{query}' with params {params}: {e}")
            try:
                self._conn.rollback()
            except:
                pass
            return False

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Executes a query with multiple sets of parameters."""
        try:
            self._cursor.executemany(query, params_list)
            self._conn.commit()
            return self._cursor.rowcount
        except Exception as e:
            logger.error(f"Error in execute_many with query '{query}': {e}")
            try:
                self._conn.rollback()
            except:
                pass
            raise

    def begin_transaction(self):
        """Begins a transaction."""
        try:
            self._conn.isolation_level = None # Autocommit off
            self._cursor.execute("BEGIN")
        except Exception as e:
            logger.error(f"Error beginning transaction: {e}")
            raise

    def commit_transaction(self):
        """Commits the current transaction."""
        try:
            self._cursor.execute("COMMIT")
            self._conn.isolation_level = '' # Reset to default
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            raise

    def rollback_transaction(self):
        """Rolls back the current transaction."""
        try:
            self._cursor.execute("ROLLBACK")
            self._conn.isolation_level = '' # Reset to default
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise

    def get_connection(self) -> sqlite3.Connection:
        """Returns the underlying database connection for direct use if needed."""
        return self._conn

    def get_cursor(self) -> sqlite3.Cursor:
        """Returns the database cursor for direct use if needed."""
        return self._cursor