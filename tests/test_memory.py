import sqlite3
import pytest
from pathlib import Path
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore

@pytest.fixture
def temp_db_mgr(tmp_path):
    db_file = str(tmp_path / "test_sam_memory.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.init_db()
    return db_mgr

@pytest.fixture
def temp_store(temp_db_mgr):
    return SkillStore(temp_db_mgr)

def test_database_manager_default_path():
    db_mgr = DatabaseManager()
    expected_path = str(Path.home() / ".sam-agent" / "sam_memory.db")
    assert db_mgr.db_path == expected_path

def test_database_manager_row_factory(temp_db_mgr):
    with temp_db_mgr.get_connection() as conn:
        assert conn.row_factory == sqlite3.Row

def test_save_and_retrieve_preference(temp_store):
    temp_store.set_preference("browser", "brave")
    assert temp_store.get_preference("browser") == "brave"
    assert temp_store.get_preference("non_existent", "default_val") == "default_val"
    assert temp_store.get_preference("non_existent") is None

    # Test update existing preference
    temp_store.set_preference("browser", "edge")
    assert temp_store.get_preference("browser") == "edge"

def test_save_and_find_skill(temp_store):
    steps = [
        {"tool": "launch_app", "params": {"name": "notepad"}},
        {"tool": "type_keyboard", "params": {"text": "hello"}}
    ]
    temp_store.save_skill(
        intent_key="buka notepad ketik hello",
        description="Buka aplikasi notepad dan ketik hello",
        steps=steps
    )

    # Exact match
    found = temp_store.find_skill("buka notepad ketik hello")
    assert found is not None
    assert len(found) == 2
    assert found[0]["tool"] == "launch_app"
    assert found[1]["params"]["text"] == "hello"

    # Case-insensitive match
    found_upper = temp_store.find_skill("BUKA NOTEPAD KETIK HELLO")
    assert found_upper is not None
    assert len(found_upper) == 2

    # Substring match: query contains intent_key
    found_sub = temp_store.find_skill("tolong buka notepad ketik hello dong")
    assert found_sub is not None
    assert len(found_sub) == 2

    # Substring match: intent_key contains query
    found_sub2 = temp_store.find_skill("notepad ketik hello")
    assert found_sub2 is not None
    assert len(found_sub2) == 2

    # Non-existent skill
    not_found = temp_store.find_skill("putar lagu di spotify")
    assert not_found is None

    # Updating skill (re-saving same intent_key)
    updated_steps = [
        {"tool": "launch_app", "params": {"name": "notepad"}},
        {"tool": "type_keyboard", "params": {"text": "hello world"}}
    ]
    temp_store.save_skill(
        intent_key="buka notepad ketik hello",
        description="Updated description",
        steps=updated_steps
    )
    found_updated = temp_store.find_skill("buka notepad ketik hello")
    assert found_updated is not None
    assert found_updated[1]["params"]["text"] == "hello world"

def test_skill_success_count_increment(temp_store, temp_db_mgr):
    steps = [{"tool": "launch_app", "params": {"name": "calc"}}]
    temp_store.save_skill("buka kalkulator", "Buka kalkulator", steps)

    with temp_db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT success_count FROM skills WHERE intent_key = ?", ("buka kalkulator",))
        row = cursor.fetchone()
        assert row["success_count"] == 1

    # Save again to simulate another successful execution
    temp_store.save_skill("buka kalkulator", "Buka kalkulator", steps)

    with temp_db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT success_count FROM skills WHERE intent_key = ?", ("buka kalkulator",))
        row = cursor.fetchone()
        assert row["success_count"] == 2
