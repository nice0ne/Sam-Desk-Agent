import pytest
from unittest.mock import MagicMock

from src.brain.prompts import SAM_SYSTEM_PROMPT
from src.brain.registry import ToolRegistry
from src.brain.agent import AgentBrain


def test_tool_registry_schemas():
    registry = ToolRegistry()
    schemas = registry.get_schemas()
    assert isinstance(schemas, list)

    tool_map = {t["function"]["name"]: t["function"] for t in schemas if t.get("type") == "function"}
    
    expected_tools = [
        "launch_application",
        "close_application",
        "adjust_system_volume",
        "type_keyboard",
        "mouse_drag",
        "web_search",
        "speak_feedback",
    ]
    for tool_name in expected_tools:
        assert tool_name in tool_map, f"Missing tool schema for {tool_name}"

    # Verify required parameters
    assert "app_name" in tool_map["launch_application"]["parameters"]["required"]
    assert "target" in tool_map["close_application"]["parameters"]["required"]
    assert "text" in tool_map["type_keyboard"]["parameters"]["required"]
    
    mouse_drag_req = tool_map["mouse_drag"]["parameters"]["required"]
    for coord in ["start_x", "start_y", "end_x", "end_y"]:
        assert coord in mouse_drag_req

    assert "query" in tool_map["web_search"]["parameters"]["required"]
    assert "message" in tool_map["speak_feedback"]["parameters"]["required"]

    # Also verify static call works
    static_schemas = ToolRegistry.get_schemas()
    assert len(static_schemas) == len(schemas)


def test_sam_system_prompt_content():
    assert "Sam" in SAM_SYSTEM_PROMPT
    assert "Windows" in SAM_SYSTEM_PROMPT
    # Tool-calling preferences: OS layer, clipboard, short Indonesian voice response
    assert "kecepatan" in SAM_SYSTEM_PROMPT.lower() or "layer 1" in SAM_SYSTEM_PROMPT.lower()
    assert "clipboard" in SAM_SYSTEM_PROMPT.lower()
    assert "indonesia" in SAM_SYSTEM_PROMPT.lower() or "suara" in SAM_SYSTEM_PROMPT.lower()


def test_execute_plan_with_desktop_and_web_search():
    mock_desktop = MagicMock()
    mock_desktop.execute_action.side_effect = [
        {"status": "success", "pid": 100},
        {"status": "success", "typed_length": 5},
    ]

    mock_search = MagicMock()
    mock_search.search.return_value = [
        {"title": "Resep Rendang Praktis", "snippet": "Bahan: daging...", "url": "https://example.com/resep"}
    ]

    brain = AgentBrain(desktop_controller=mock_desktop, web_search_tool=mock_search)

    actions = [
        {"tool": "launch_application", "params": {"app_name": "notepad"}},
        {"tool": "web_search", "params": {"query": "resep rendang praktis"}},
        {"tool": "type_keyboard", "params": {"text": "halo", "use_clipboard": True}},
    ]

    results = brain.execute_plan(actions)

    assert len(results) == 3
    assert results[0]["tool"] == "launch_application"
    assert results[0]["result"]["status"] == "success"
    mock_desktop.execute_action.assert_any_call("launch_application", {"app_name": "notepad"})

    assert results[1]["tool"] == "web_search"
    assert len(results[1]["result"]) == 1
    assert results[1]["result"][0]["title"] == "Resep Rendang Praktis"
    mock_search.search.assert_called_once_with("resep rendang praktis")

    assert results[2]["tool"] == "type_keyboard"
    assert results[2]["result"]["status"] == "success"
    mock_desktop.execute_action.assert_any_call("type_keyboard", {"text": "halo", "use_clipboard": True})


def test_find_matching_skill_none_when_no_store():
    mock_desktop = MagicMock()
    brain = AgentBrain(desktop_controller=mock_desktop)
    assert brain.find_matching_skill("buka notepad") is None


def test_find_matching_skill_and_execution_when_cached():
    mock_desktop = MagicMock()
    mock_desktop.execute_action.return_value = {"status": "success", "pid": 200}

    mock_store = MagicMock()
    cached_steps = [
        {"tool": "launch_application", "params": {"app_name": "notepad"}}
    ]
    mock_store.find_skill.return_value = cached_steps

    brain = AgentBrain(desktop_controller=mock_desktop, skill_store=mock_store)

    # 1. Test finding matching skill
    matched = brain.find_matching_skill("buka aplikasi catatan")
    mock_store.find_skill.assert_called_once_with("buka aplikasi catatan")
    assert matched == cached_steps

    # 2. Test executing the retrieved skill actions
    results = brain.execute_plan(matched)
    assert len(results) == 1
    assert results[0]["tool"] == "launch_application"
    assert results[0]["result"]["status"] == "success"
    mock_desktop.execute_action.assert_called_once_with("launch_application", {"app_name": "notepad"})


def test_execute_plan_handles_alternate_keys_and_json_strings():
    mock_desktop = MagicMock()
    mock_desktop.execute_action.return_value = {"status": "success"}

    brain = AgentBrain(desktop_controller=mock_desktop)

    # Alternate key: 'action' instead of 'tool', 'args' instead of 'params', JSON string arguments
    actions = [
        {"action": "close_application", "args": '{"target": "notepad"}'}
    ]
    results = brain.execute_plan(actions)
    assert len(results) == 1
    assert results[0]["tool"] == "close_application"
    mock_desktop.execute_action.assert_called_once_with("close_application", {"target": "notepad"})


def test_init_exports():
    import src.brain as brain_pkg
    assert hasattr(brain_pkg, "ToolRegistry")
    assert hasattr(brain_pkg, "AgentBrain")
    assert hasattr(brain_pkg, "SAM_SYSTEM_PROMPT")
    assert hasattr(brain_pkg, "LLMClient")


def test_agent_brain_process_command_with_llm():
    mock_desktop = MagicMock()
    mock_desktop.execute_action.return_value = {"status": "success"}

    mock_llm = MagicMock()
    planned_actions = [{"tool": "launch_application", "params": {"app_name": "calc"}}]
    mock_llm.plan_actions.return_value = (planned_actions, "Membuka kalkulator.")

    mock_store = MagicMock()
    mock_store.find_skill.return_value = None  # Not in cache

    brain = AgentBrain(desktop_controller=mock_desktop, skill_store=mock_store, llm_client=mock_llm)

    res = brain.process_command("buka kalkulator dong")

    assert res["matched"] is True
    assert res["source"] == "llm_generation"
    assert res["actions"] == planned_actions
    assert len(res["results"]) == 1
    assert res["response"] == "Membuka kalkulator."
    mock_desktop.execute_action.assert_called_once_with("launch_application", {"app_name": "calc"})
    mock_store.save_skill.assert_called_once_with(
        "buka kalkulator dong",
        "Generated via LLM planning",
        planned_actions,
    )

