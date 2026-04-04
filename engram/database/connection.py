# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""SQLite connection and sqlite-vec loader for ENGRAM."""

import sqlite3

import sqlite_vec

from config import settings


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and load the sqlite-vec extension.

    Args:
        db_path: Path to the SQLite database file. Defaults to settings.db_path.

    Returns:
        sqlite3.Connection: Configured connection with WAL mode, foreign keys,
            and row_factory set to sqlite3.Row.
    """
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    # Load sqlite-vec extension
    sqlite_vec.load(conn)

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys=ON")

    return conn
