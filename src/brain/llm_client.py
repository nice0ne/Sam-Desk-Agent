"""Unified Multi-AI Provider LLM Client for Sam-Desk-Agent.

Supports OpenAI-compatible APIs including GLM (ZhipuAI), OpenAI, DeepSeek,
Groq, Ollama (Local), Google Gemini, and Generic Custom OpenAI endpoints.
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from src.brain.prompts import SAM_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "glm": {
        "name": "GLM (ZhipuAI)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-4-plus",
        "env_var": "GLM_API_KEY",
        "alt_env_vars": ["ZHIPUAI_API_KEY", "ZHIPU_API_KEY"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_var": "OPENAI_API_KEY",
        "alt_env_vars": [],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_var": "DEEPSEEK_API_KEY",
        "alt_env_vars": [],
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_var": "GROQ_API_KEY",
        "alt_env_vars": [],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:7b",
        "env_var": "OLLAMA_API_KEY",
        "alt_env_vars": [],
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
        "env_var": "GEMINI_API_KEY",
        "alt_env_vars": [],
    },
    "custom": {
        "name": "Custom OpenAI-Compatible",
        "base_url": "",
        "default_model": "default",
        "env_var": "CUSTOM_AI_API_KEY",
        "alt_env_vars": ["AI_API_KEY"],
    },
}


@dataclass
class LLMProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    max_sub_actions: int = 10


def get_default_provider_config(provider: str) -> LLMProviderConfig:
    """Returns default provider configuration using known presets."""
    preset = PROVIDER_PRESETS.get(provider.lower(), PROVIDER_PRESETS["custom"])
    env_var = preset.get("env_var", "")
    api_key = os.environ.get(env_var, "")
    if not api_key:
        for alt in preset.get("alt_env_vars", []):
            if alt in os.environ:
                api_key = os.environ[alt]
                break

    return LLMProviderConfig(
        provider=provider.lower(),
        model=preset.get("default_model", "glm-4-flash"),
        base_url=preset.get("base_url", ""),
        api_key=api_key or ("ollama" if provider == "ollama" else ""),
    )


class LLMClient:
    """Unified client for multi-AI provider tool calling and reasoning."""

    def __init__(
        self,
        provider: str = "glm",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_sub_actions: int = 10,
    ) -> None:
        self.provider = provider.lower()
        preset = PROVIDER_PRESETS.get(self.provider, PROVIDER_PRESETS["custom"])

        self.model = model or preset.get("default_model", "glm-4-flash")
        self.base_url = (base_url or preset.get("base_url", "")).strip()

        # Resolve API Key: explicit > primary env > alt envs > dummy for local
        resolved_key = (api_key or "").strip()
        if not resolved_key:
            env_var = preset.get("env_var", "")
            resolved_key = os.environ.get(env_var, "").strip()
            if not resolved_key:
                for alt in preset.get("alt_env_vars", []):
                    if alt in os.environ:
                        resolved_key = os.environ[alt].strip()
                        break
        if not resolved_key and self.provider == "ollama":
            resolved_key = "ollama"

        self.api_key = resolved_key
        self.max_sub_actions = max_sub_actions
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                kwargs: Dict[str, Any] = {
                    "api_key": self.api_key or "missing_key",
                }
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                # Silently fallback to native HTTP caller if openai package is not installed
                self._client = None
            except Exception as e:
                logger.debug("Could not initialize OpenAI SDK client: %s", e)
                self._client = None
        return self._client

    def _call_api_http(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Direct HTTP POST to OpenAI-compatible /chat/completions endpoint using standard urllib."""
        import urllib.request
        import urllib.error

        base = self.base_url.rstrip("/")
        if not base:
            raise ValueError(f"Base URL for provider '{self.provider}' is not configured.")

        if base.endswith("/chat/completions"):
            url = base
        else:
            url = f"{base}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_res = resp.read().decode("utf-8")
                return json.loads(raw_res)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("[%s] HTTP Error %s: %s", self.provider.upper(), e.code, err_body)
            raise RuntimeError(f"HTTP Error {e.code}: {err_body}") from e
        except urllib.error.URLError as e:
            logger.error("[%s] Network Error: %s", self.provider.upper(), e.reason)
            raise RuntimeError(f"Network Error: {e.reason}") from e

    def plan_actions(
        self,
        user_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Sends user query and available tools to the LLM, extracting structured action plans.

        Returns:
            Tuple of (list of action dictionaries, textual assistant response).
        """
        messages = [
            {"role": "system", "content": system_prompt or SAM_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 1. Try via OpenAI SDK if available
        client = self._get_client()
        if client is not None:
            try:
                response = client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message
                content = message.content or ""
                actions: List[Dict[str, Any]] = []

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for call in message.tool_calls:
                        fn_name = call.function.name
                        raw_args = call.function.arguments
                        try:
                            params = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                        except Exception:
                            params = {"raw": raw_args}
                        actions.append({"tool": fn_name, "params": params})

                if len(actions) > self.max_sub_actions:
                    actions = actions[:self.max_sub_actions]

                return actions, content
            except Exception as e:
                logger.warning(
                    "Error calling %s via SDK: %s. Trying direct HTTP fallback.",
                    self.provider.upper(), e
                )

        # 2. Fallback to direct HTTP API call (pure standard library, 0 external dependencies)
        try:
            res = self._call_api_http(kwargs)
            choices = res.get("choices", [])
            if not choices:
                return [], f"[{self.provider.upper()}] Empty response from API: {res}"

            msg = choices[0].get("message", {})
            content = msg.get("content") or ""
            actions: List[Dict[str, Any]] = []

            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for call in tool_calls:
                    fn = call.get("function", {})
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            params = json.loads(raw_args) if raw_args else {}
                        except Exception:
                            params = {"raw": raw_args}
                    else:
                        params = raw_args or {}
                    actions.append({"tool": fn_name, "params": params})

            if len(actions) > self.max_sub_actions:
                actions = actions[:self.max_sub_actions]

            return actions, content
        except Exception as e:
            logger.error("Error during %s completion: %s", self.provider.upper(), e)
            return [], f"[{self.provider.upper()} Error] {e}"

    def test_connection(self) -> Tuple[bool, str]:
        """Tests the connection to the configured AI provider with current credentials and model.

        Returns:
            Tuple of (success_bool, message_str).
        """
        if not self.api_key and self.provider != "ollama":
            return False, "API Key belum diisi. Masukkan API Key terlebih dahulu."

        import time
        start_time = time.time()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "ping"}
            ],
            "max_tokens": 15,
        }

        # 1. Try SDK if client initialized
        client = self._get_client()
        if client is not None:
            try:
                resp = client.chat.completions.create(**payload)
                elapsed = int((time.time() - start_time) * 1000)
                return True, f"Koneksi Berhasil ({elapsed}ms)! Model '{self.model}' aktif."
            except Exception as e:
                logger.debug("SDK test_connection error: %s. Trying direct HTTP fallback.", e)

        # 2. Native HTTP fallback
        try:
            res = self._call_api_http(payload)
            elapsed = int((time.time() - start_time) * 1000)
            choices = res.get("choices", [])
            if not choices:
                return False, f"Respons kosong dari server: {res}"
            return True, f"Koneksi Berhasil ({elapsed}ms)! Model '{self.model}' aktif."
        except Exception as e:
            err_msg = str(e)
            logger.error("[%s] Test connection failed: %s", self.provider.upper(), err_msg)
            if "401" in err_msg:
                return False, "Autentikasi Gagal (401): API Key tidak valid atau unauthorized."
            elif "404" in err_msg:
                return False, f"Tidak Ditemukan (404): Periksa Nama Model '{self.model}' atau Base URL."
            elif "429" in err_msg:
                return False, "Batas Kuota / Rate Limit (429): Kuota API habis atau request berlebih."
            return False, f"Gagal terhubung: {err_msg[:120]}"

