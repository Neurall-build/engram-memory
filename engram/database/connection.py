# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""SQLite connection and sqlite-vec loader for ENGRAM."""

import sqlite3
import threading

import sqlite_vec

from config import settings

# Singleton connection for in-memory databases (each :memory: connection is a separate DB)
_connection = None
_connection_lock = threading.Lock()

# Write lock for thread safety with check_same_thread=False
# SQLite only allows one writer at a time; this serializes write operations
_write_lock = threading.Lock()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and load the sqlite-vec extension.

    For :memory: databases, returns a singleton connection to ensure
    all operations use the same in-memory database.

    Args:
        db_path: Path to the SQLite database file. Defaults to settings.db_path.

    Returns:
        sqlite3.Connection: Configured connection with WAL mode, foreign keys,
            and row_factory set to sqlite3.Row.
    """
    global _connection
    path = db_path or settings.db_path

    # For in-memory databases, use singleton to avoid separate DB per connection
    if path == ":memory:":
        with _connection_lock:
            if _connection is None:
                _connection = _create_connection(path)
            return _connection

    return _create_connection(path)


def reset_connection():
    """Reset the singleton connection (useful for test cleanup)."""
    global _connection
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.close()
            except Exception:
                pass
            _connection = None


def _create_connection(path: str) -> sqlite3.Connection:
    """Create and configure a new SQLite connection.

    Note: check_same_thread=False is required for async FastAPI usage
    but means callers MUST use execute_write() for write operations
    to ensure thread safety.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enable extension loading (required for sqlite-vec)
    conn.enable_load_extension(True)

    # Load sqlite-vec extension
    sqlite_vec.load(conn)

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def execute_write(conn, sql: str, params: tuple = ()):
    """Execute a write operation on the connection in a thread-safe manner.

    This serializes write operations using a lock to prevent data corruption
    when check_same_thread=False is used.
    """
    with _write_lock:
        return conn.execute(sql, params)


def execute_writemany(conn, sql: str, params_list: list):
    """Execute multiple write operations in a thread-safe manner."""
    with _write_lock:
        return conn.executemany(sql, params_list)
