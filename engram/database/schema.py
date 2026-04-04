# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Database schema definitions and initialization for ENGRAM."""

from database.connection import get_connection
from config import settings


def _create_working_memory(conn):
    """Create the working_memory table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS working_memory (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            salience REAL DEFAULT 0.5,
            created_at REAL NOT NULL,
            expires_at REAL
        )
    """)


def _create_episodic_memory(conn):
    """Create the episodic_memory table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            salience REAL DEFAULT 0.5,
            created_at REAL NOT NULL,
            expires_at REAL,
            decay_score REAL DEFAULT 1.0,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL NOT NULL,
            promoted INTEGER DEFAULT 0
        )
    """)


def _create_semantic_memory(conn):
    """Create the semantic_memory table and semantic_vectors virtual table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            salience REAL DEFAULT 0.5,
            created_at REAL NOT NULL,
            expires_at REAL,
            decay_score REAL DEFAULT 1.0,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL NOT NULL,
            source_episode TEXT
        )
    """)

    embed_dim = settings.embed_dim
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS semantic_vectors USING vec0(
            memory_id TEXT PRIMARY KEY,
            embedding float[{embed_dim}]
        )
    """)


def _create_hive_memory(conn):
    """Create the hive_memory table and hive_vectors virtual table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hive_memory (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT,
            org_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            salience REAL DEFAULT 0.5,
            created_at REAL NOT NULL,
            expires_at REAL,
            decay_score REAL DEFAULT 1.0,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL NOT NULL,
            visibility TEXT DEFAULT 'org'
        )
    """)

    embed_dim = settings.embed_dim
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS hive_vectors USING vec0(
            memory_id TEXT PRIMARY KEY,
            embedding float[{embed_dim}]
        )
    """)


def init_db():
    """Initialize the database schema.

    Creates all tables and virtual tables if they do not exist.
    """
    conn = get_connection()
    try:
        _create_working_memory(conn)
        _create_episodic_memory(conn)
        _create_semantic_memory(conn)
        _create_hive_memory(conn)
        conn.commit()
    finally:
        conn.close()
