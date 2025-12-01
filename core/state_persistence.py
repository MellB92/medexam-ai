"""State persistence with SQLite database."""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class StatePersistence:
    """Handles state persistence to SQLite database."""

    def __init__(self, db_path: str = 'session_state.db'):
        """Initialize persistence layer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                total_tokens INTEGER,
                total_docs INTEGER,
                total_cost REAL,
                status TEXT,
                provider TEXT
            )
        ''')

        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                path TEXT,
                tokens INTEGER,
                processed_at TIMESTAMP,
                provider TEXT,
                success BOOLEAN,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        # Handovers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS handovers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                created_at TIMESTAMP,
                tokens_used INTEGER,
                docs_processed INTEGER,
                handover_data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"✅ Database initialized: {self.db_path}")

    def save_session(self, session_data: Dict[str, Any]):
        """Save session to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO sessions
            (id, started_at, ended_at, total_tokens, total_docs, total_cost, status, provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data['id'],
            session_data['started_at'],
            session_data.get('ended_at'),
            session_data.get('context_tokens', 0),
            len(session_data.get('processed_docs', [])),
            session_data.get('budget_used', 0.0),
            session_data.get('status', 'active'),
            session_data.get('current_provider')
        ))

        conn.commit()
        conn.close()

    def save_document(self, session_id: str, doc_data: Dict[str, Any]):
        """Save document processing record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO documents
            (session_id, path, tokens, processed_at, provider, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            doc_data['path'],
            doc_data['tokens'],
            doc_data['timestamp'],
            doc_data['provider'],
            True  # Assume success if we got here
        ))

        conn.commit()
        conn.close()

    def save_handover(self, session_id: str, handover_data: Dict[str, Any]):
        """Save handover record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO handovers
            (session_id, created_at, tokens_used, docs_processed, handover_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session_id,
            datetime.now().isoformat(),
            handover_data.get('total_tokens', 0),
            handover_data.get('processed_count', 0),
            json.dumps(handover_data)
        ))

        conn.commit()
        conn.close()

    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM documents
            WHERE session_id = ?
            ORDER BY processed_at
        ''', (session_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
