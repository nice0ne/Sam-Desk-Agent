import json
from typing import Optional, List, Dict, Any
from src.memory.db import DatabaseManager

class SkillStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def set_preference(self, key: str, value: str) -> None:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (key, value)
            )
            conn.commit()

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def save_skill(self, intent_key: str, description: str, steps: List[Dict[str, Any]]) -> None:
        normalized_key = intent_key.strip().lower()
        steps_json = json.dumps(steps)
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO skills (intent_key, description, steps_json, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(intent_key) DO UPDATE SET steps_json=excluded.steps_json, description=excluded.description, "
                "success_count=success_count+1, updated_at=CURRENT_TIMESTAMP",
                (normalized_key, description, steps_json)
            )
            conn.commit()

    def find_skill(self, query: str) -> Optional[List[Dict[str, Any]]]:
        normalized_query = query.strip().lower()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Exact match
            cursor.execute("SELECT steps_json FROM skills WHERE intent_key = ?", (normalized_query,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["steps_json"])

            # 2. Substring match fallback (query contains intent_key or intent_key contains query)
            cursor.execute(
                "SELECT steps_json FROM skills WHERE (? LIKE '%' || intent_key || '%') OR (intent_key LIKE '%' || ? || '%') "
                "ORDER BY LENGTH(intent_key) DESC LIMIT 1",
                (normalized_query, normalized_query)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["steps_json"])
            return None
