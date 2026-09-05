import sqlite3
from pathlib import Path
from typing import Optional

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            home = Path.home() / ".sam-agent"
            home.mkdir(parents=True, exist_ok=True)
            db_path = str(home / "sam_memory.db")
        else:
            # Ensure parent dir exists if a specific path is given
            parent = Path(db_path).parent
            if parent:
                parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)

    def get_connection(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if not hasattr(self, "_memory_conn") or self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_key TEXT UNIQUE NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()
