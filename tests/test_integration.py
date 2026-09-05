import pytest
from unittest.mock import patch
from src.core.event_bus import EventBus
from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.brain.agent import AgentBrain
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore
from src.ui.hud import FloatingHUD, HUDState

def test_full_pipeline_smoke(tmp_path):
    bus = EventBus()
    safety = SafetySupervisor(bus)
    desktop = DesktopActionController(safety)
    db_file = str(tmp_path / "smoke_memory.db")
    db = DatabaseManager(db_file)
    db.init_db()
    skill_store = SkillStore(db)
    hud = FloatingHUD()
    brain = AgentBrain(desktop, skill_store)

    # 1. Test HUD state transitions
    hud.update_state(HUDState.LISTENING, "Mendengarkan instruksi...")
    state, msg = hud.get_current_state()
    assert state == HUDState.LISTENING
    assert "Mendengarkan" in msg

    # 2. Test execution of adjust volume action via brain
    with patch.object(desktop.os_ctrl, "adjust_volume", return_value=0.4):
        results = brain.execute_plan([
            {"tool": "adjust_system_volume", "params": {"level": 0.4}}
        ])
        assert len(results) == 1
        assert results[0]["result"]["status"] == "success"

    # 3. Test saving and finding procedural skill
    skill_store.save_skill(
        intent_key="atur volume santai",
        description="Atur volume ke 40%",
        steps=[{"tool": "adjust_system_volume", "params": {"level": 0.4}}]
    )
    found_plan = brain.find_matching_skill("atur volume santai")
    assert found_plan is not None
    assert len(found_plan) == 1
    assert found_plan[0]["tool"] == "adjust_system_volume"

    # 4. Test safety interruption prevents execution
    safety.trigger_panic("Pengujian Panic Stop")
    cancelled_results = brain.execute_plan([
        {"tool": "adjust_system_volume", "params": {"level": 0.8}}
    ])
    assert cancelled_results[0]["result"]["status"] == "cancelled"

def test_multi_tool_chain_pipeline(tmp_path):
    bus = EventBus()
    safety = SafetySupervisor(bus)
    desktop = DesktopActionController(safety)
    db_file = str(tmp_path / "chain_memory.db")
    db = DatabaseManager(db_file)
    db.init_db()
    skill_store = SkillStore(db)
    brain = AgentBrain(desktop, skill_store)

    # Simulate multi-step tool chain:
    # 1. web_search
    # 2. type_keyboard
    actions = [
        {"tool": "web_search", "params": {"query": "resep nasi goreng"}},
        {"tool": "type_keyboard", "params": {"text": "Resep Nasi Goreng Siap", "use_clipboard": True}}
    ]

    with patch.object(desktop.mk_ctrl, "type_text") as mock_type:
        results = brain.execute_plan(actions)
        assert len(results) == 2
        assert results[0]["tool"] == "web_search"
        assert isinstance(results[0]["result"], list)
        assert results[1]["tool"] == "type_keyboard"
        assert results[1]["result"]["status"] == "success"
        mock_type.assert_called_once_with("Resep Nasi Goreng Siap", True)
