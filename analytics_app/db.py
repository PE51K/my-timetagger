#!/usr/bin/env python3
"""
Database connection script for Timetagger SQLite database.

This script provides a connection interface to the Timetagger database
located at data/timetagger/_timetagger/users/pe51k~cGU1MWs=.db
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TimetaggerDB:
    """Class to handle connections and queries to the Timetagger database."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to the database file. If None, uses default path from environment or default location.
        """
        if db_path is None:
            import os

            # Try to get from environment variable (for Docker)
            env_db_path = os.getenv("TIMETAGGER_DB_PATH")
            if env_db_path and Path(env_db_path).exists():
                db_path = env_db_path
            else:
                # Try to find database file in common locations
                db_path = self._find_database_file()

                if db_path is None:
                    raise FileNotFoundError(
                        "Database file not found. Please set TIMETAGGER_DB_PATH environment variable "
                        "or ensure the database is accessible."
                    )

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        self.conn: Optional[sqlite3.Connection] = None

    @staticmethod
    def _find_database_file() -> Optional[Path]:
        """Try to find the database file in common locations."""
        import os

        # Possible base paths to search
        search_paths = []

        # 1. Check TIMETAGGER_DATADIR environment variable
        timetagger_datadir = os.getenv("TIMETAGGER_DATADIR")
        if timetagger_datadir:
            search_paths.append(Path(timetagger_datadir))

        # 2. Common Docker volume mount paths
        search_paths.extend(
            [
                Path("/data/timetagger"),
                Path("/data"),
                Path("/app/data"),
            ]
        )

        # 3. Local development path
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        search_paths.append(project_root / "data" / "timetagger")

        # Search for database files in users directory
        db_filename = "pe51k~cGU1MWs=.db"

        # Try direct paths and recursive search
        for base in search_paths:
            # Search recursively for the database file
            if base.exists():
                for db_file in base.rglob(db_filename):
                    if db_file.is_file():
                        return db_file

                # Try the expected structure
                expected_path = base / "_timetagger" / "users" / db_filename
                if expected_path.exists():
                    return expected_path

        # If not found, try any .db file in users directory
        for base in search_paths:
            users_dir = base / "_timetagger" / "users"
            if users_dir.exists():
                db_files = list(users_dir.glob("*.db"))
                if db_files:
                    # Return the first one found
                    return db_files[0]

        return None

    def connect(self):
        """Establish connection to the database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        return self.conn

    def disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters for prepared statements

        Returns:
            List of dictionaries representing rows
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query: SQL query string
            params: Query parameters for prepared statements

        Returns:
            Number of affected rows
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount

    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = self.execute_query(query)
        return [row["name"] for row in result]

    def get_table_schema(self, table_name: str) -> str:
        """Get the CREATE TABLE statement for a given table."""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else ""

    def get_records_count(self) -> int:
        """Get total number of records."""
        query = "SELECT COUNT(*) as count FROM records"
        result = self.execute_query(query)
        return result[0]["count"] if result else 0

    def get_userinfo(self) -> List[Dict[str, Any]]:
        """Get all userinfo entries."""
        return self.execute_query("SELECT * FROM userinfo")

    def get_settings(self) -> List[Dict[str, Any]]:
        """Get all settings entries."""
        return self.execute_query("SELECT * FROM settings")

    def get_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get records from the database.

        Args:
            limit: Maximum number of records to return (None for all)

        Returns:
            List of record dictionaries
        """
        query = "SELECT * FROM records ORDER BY t1 DESC"
        if limit:
            query += " LIMIT {}".format(limit)
        return self.execute_query(query)

    def get_parsed_records(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get records with parsed JSON _ob field and extracted tags.

        Args:
            start_date: Filter records starting from this date (inclusive)
            end_date: Filter records ending before this date (inclusive)

        Returns:
            List of parsed record dictionaries with:
            - key: record key
            - t1: start timestamp
            - t2: end timestamp
            - duration: duration in seconds
            - description: description text
            - tags: list of tags (ordered by appearance)
            - datetime_start: datetime object for t1
            - datetime_end: datetime object for t2
        """
        query = "SELECT _ob, t1, t2 FROM records WHERE 1=1"
        params = []

        if start_date:
            query += " AND t1 >= ?"
            params.append(int(start_date.timestamp()))

        if end_date:
            query += " AND t2 <= ?"
            params.append(int(end_date.timestamp()))

        query += " ORDER BY t1 DESC"

        raw_records = self.execute_query(query, tuple(params))
        parsed_records = []

        for record in raw_records:
            try:
                _ob = json.loads(record["_ob"])
                t1 = record["t1"]
                t2 = record["t2"]
                description = _ob.get("ds", "")
                tags = self._extract_tags(description)

                parsed_record = {
                    "key": _ob.get("key", ""),
                    "t1": t1,
                    "t2": t2,
                    "duration": t2 - t1 if t2 and t1 else 0,
                    "description": description,
                    "tags": tags,
                    "datetime_start": datetime.fromtimestamp(t1) if t1 else None,
                    "datetime_end": datetime.fromtimestamp(t2) if t2 else None,
                }
                parsed_records.append(parsed_record)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip malformed records
                continue

        return parsed_records

    @staticmethod
    def _extract_tags(description: str) -> List[str]:
        """
        Extract tags from description string.
        Tags are words starting with #.

        Args:
            description: Description string containing tags

        Returns:
            List of tags in order of appearance (without #)
        """
        if not description:
            return []

        # Find all tags (words starting with #)
        tag_pattern = r"#(\w+)"
        tags = re.findall(tag_pattern, description)
        return tags

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def main():
    """Example usage of the TimetaggerDB class."""
    # Example 1: Using context manager (recommended)
    print("=== Timetagger Database Connection Example ===\n")

    with TimetaggerDB() as db:
        # Get all tables
        print("Tables in database:")
        tables = db.get_tables()
        for table in tables:
            print(f"  - {table}")

        print("\n" + "=" * 50 + "\n")

        # Get record count
        count = db.get_records_count()
        print(f"Total records: {count}")

        print("\n" + "=" * 50 + "\n")

        # Get recent records (limit 5)
        print("Recent records (last 5):")
        records = db.get_records(limit=5)
        for record in records:
            print(f"  Key: {record.get('key', 'N/A')}")
            print(f"    t1: {record.get('t1', 'N/A')}, t2: {record.get('t2', 'N/A')}")
            print()

        print("=" * 50 + "\n")

        # Get userinfo
        print("User info:")
        userinfo = db.get_userinfo()
        for info in userinfo:
            print(f"  Key: {info.get('key', 'N/A')}")
            print(f"    st: {info.get('st', 'N/A')}")
            print()

        print("=" * 50 + "\n")

        # Get settings
        print("Settings:")
        settings = db.get_settings()
        for setting in settings:
            print(f"  Key: {setting.get('key', 'N/A')}")
            print(f"    st: {setting.get('st', 'N/A')}")
            print()


if __name__ == "__main__":
    main()
