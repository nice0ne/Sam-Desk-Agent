import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.brain.registry import ToolRegistry
from src.brain.llm_client import (
    LLMClient,
    LLMProviderConfig,
    PROVIDER_PRESETS,
    get_default_provider_config,
)


def test_provider_presets():
    expected_providers = ["glm", "openai", "deepseek", "groq", "ollama", "gemini", "custom"]
    for p in expected_providers:
        assert p in PROVIDER_PRESETS
        preset = PROVIDER_PRESETS[p]
        assert "default_model" in preset
        assert "base_url" in preset
        assert "env_var" in preset


def test_get_default_provider_config():
    glm_cfg = get_default_provider_config("glm")
    assert glm_cfg.provider == "glm"
    assert "bigmodel.cn" in glm_cfg.base_url
    assert glm_cfg.model == "glm-4-plus"

    ollama_cfg = get_default_provider_config("ollama")
    assert "11434" in ollama_cfg.base_url
    assert ollama_cfg.model == "qwen2.5:7b"


def test_llm_client_api_key_resolution(monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "test-glm-key-123")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # 1. Resolves from env
    client = LLMClient(provider="glm")
    assert client.api_key == "test-glm-key-123"
    assert "bigmodel.cn" in client.base_url

    # 2. Explicit config overrides env
    custom_client = LLMClient(
        provider="glm",
        api_key="explicit-key",
        base_url="https://custom.glm.proxy/v1"
    )
    assert custom_client.api_key == "explicit-key"
    assert custom_client.base_url == "https://custom.glm.proxy/v1"


def test_llm_client_plan_actions_with_tool_calls():
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "launch_application"
    mock_tool_call.function.arguments = json.dumps({"app_name": "notepad"})

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = "Membuka aplikasi Notepad."

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    client = LLMClient(provider="glm", api_key="dummy-key")
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = mock_completion

    schemas = ToolRegistry.get_schemas()
    actions, text_response = client.plan_actions("buka notepad", tools=schemas)

    assert len(actions) == 1
    assert actions[0]["tool"] == "launch_application"
    assert actions[0]["params"] == {"app_name": "notepad"}
    assert text_response == "Membuka aplikasi Notepad."


def test_llm_client_plan_actions_plain_text():
    mock_message = MagicMock()
    mock_message.tool_calls = None
    mock_message.content = "Halo! Ada yang bisa saya bantu?"

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    client = LLMClient(provider="openai", api_key="dummy-key")
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = mock_completion

    actions, text_response = client.plan_actions("halo", tools=[])
    assert actions == []
    assert text_response == "Halo! Ada yang bisa saya bantu?"


def test_llm_client_plan_actions_error_handling():
    client = LLMClient(provider="deepseek", api_key="dummy-key")
    client._client = MagicMock()
    client._client.chat.completions.create.side_effect = Exception("API connection timed out")
    # Both SDK and HTTP fail
    with patch.object(client, "_call_api_http", side_effect=RuntimeError("HTTP Failed")):
        actions, text_response = client.plan_actions("buka kalkulator", tools=[])
        assert actions == []
        assert "HTTP Failed" in text_response


def test_llm_client_native_http_tool_calling():
    client = LLMClient(provider="glm", api_key="dummy-key")
    # Ensure SDK is None to test pure native HTTP path
    client._client = None
    with patch.dict("sys.modules", {"openai": None}):
        fake_http_response = {
            "choices": [
                {
                    "message": {
                        "content": "Volume dinaikkan.",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "adjust_system_volume",
                                    "arguments": json.dumps({"delta": 0.3})
                                }
                            }
                        ]
                    }
                }
            ]
        }
        with patch.object(client, "_call_api_http", return_value=fake_http_response) as mock_http:
            actions, content = client.plan_actions("naikkan volume 30%", tools=[{"name": "adjust_system_volume"}])
            mock_http.assert_called_once()
            assert len(actions) == 1
            assert actions[0]["tool"] == "adjust_system_volume"
            assert actions[0]["params"] == {"delta": 0.3}
            assert content == "Volume dinaikkan."


def test_llm_client_native_http_plain_text():
    client = LLMClient(provider="glm", api_key="dummy-key")
    client._client = None
    with patch.dict("sys.modules", {"openai": None}):
        fake_http_response = {
            "choices": [
                {
                    "message": {
                        "content": "Halo! Saya Sam.",
                    }
                }
            ]
        }
        with patch.object(client, "_call_api_http", return_value=fake_http_response) as mock_http:
            actions, content = client.plan_actions("halo", tools=[])
            mock_http.assert_called_once()
            assert actions == []
            assert content == "Halo! Saya Sam."


def test_llm_client_test_connection_success():
    client = LLMClient(provider="glm", model="glm-4-plus", api_key="dummy-key")
    client._client = None
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": "OK",
                }
            }
        ]
    }
    with patch.object(client, "_call_api_http", return_value=fake_response):
        success, msg = client.test_connection()
        assert success is True
        assert "Koneksi Berhasil" in msg
        assert "glm-4-plus" in msg


def test_llm_client_test_connection_failure():
    client = LLMClient(provider="glm", model="invalid-model", api_key="dummy-key")
    client._client = None
    with patch.object(client, "_call_api_http", side_effect=RuntimeError("HTTP Error 400: Model not found")):
        success, msg = client.test_connection()
        assert success is False
        assert "Gagal" in msg
        assert "Model not found" in msg
