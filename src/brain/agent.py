import json
import logging
from typing import Dict, Any, List, Optional

from src.brain.prompts import SAM_SYSTEM_PROMPT
from src.brain.registry import ToolRegistry
from src.tools.web_search import WebSearchTool
from src.memory.skill_store import SkillStore

logger = logging.getLogger(__name__)

try:
    from src.desktop.controller import DesktopActionController
except ImportError:
    DesktopActionController = Any  # type: ignore


class AgentBrain:
    """Core brain of Sam-Desk-Agent handling plan execution, skill matching, and LLM reasoning."""

    def __init__(
        self,
        desktop_controller: Any,
        skill_store: Optional[SkillStore] = None,
        web_search_tool: Optional[WebSearchTool] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        self.desktop = desktop_controller
        self.skill_store = skill_store
        self.web_search = web_search_tool if web_search_tool is not None else WebSearchTool()
        self.registry = ToolRegistry()
        self.llm_client = llm_client

    def find_matching_skill(self, user_text: str) -> Optional[List[Dict[str, Any]]]:
        """Checks skill_store for cached actions matching the user text."""
        if self.skill_store is not None:
            return self.skill_store.find_skill(user_text)
        return None

    def execute_plan(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes a list of tool actions sequentially."""
        results = []
        for step in actions:
            tool_name = step.get("tool") or step.get("name") or step.get("action")
            params = step.get("params")
            if params is None:
                params = step.get("parameters")
            if params is None:
                params = step.get("args", {})

            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except Exception:
                    params = {"raw": params}

            if not isinstance(params, dict):
                params = {}

            if tool_name == "web_search":
                query = params.get("query", "")
                if "max_results" in params:
                    res = self.web_search.search(query, max_results=params["max_results"])
                else:
                    res = self.web_search.search(query)
                results.append({"tool": tool_name, "result": res})
            else:
                if self.desktop is not None and hasattr(self.desktop, "execute_action"):
                    res = self.desktop.execute_action(tool_name, params)
                else:
                    res = {
                        "status": "error",
                        "message": f"Desktop controller unavailable or cannot execute action: {tool_name}",
                    }
                results.append({"tool": tool_name, "result": res})

        return results

    def process_command(self, user_text: str) -> Dict[str, Any]:
        """Processes a user command: checks cached skills first, then falls back to LLM planning."""
        cached_steps = self.find_matching_skill(user_text)
        if cached_steps:
            results = self.execute_plan(cached_steps)
            return {
                "source": "skill_cache",
                "matched": True,
                "actions": cached_steps,
                "results": results,
                "response": "Alur aksi dari memori berhasil dijalankan.",
            }

        # If not in cache and LLM client is available, plan actions dynamically
        if self.llm_client is not None:
            schemas = self.registry.get_schemas()
            actions, text_response = self.llm_client.plan_actions(user_text, tools=schemas)
            if actions:
                for act in actions:
                    if act.get("tool") in ("speak_feedback", "speak"):
                        spoken = act.get("params", {}).get("message") or act.get("params", {}).get("text")
                        if spoken:
                            text_response = spoken
                            break

                results = self.execute_plan(actions)

                # Auto-save successful action sequences to self-learning skill store
                all_succeeded = all(
                    isinstance(r.get("result"), dict) and r.get("result", {}).get("status") != "error"
                    for r in results
                )
                if all_succeeded and self.skill_store is not None:
                    try:
                        self.skill_store.save_skill(
                            user_text,
                            "Generated via LLM planning",
                            actions,
                        )
                    except Exception as e:
                        logger.warning("Could not auto-save learned skill: %s", e)

                return {
                    "source": "llm_generation",
                    "matched": True,
                    "actions": actions,
                    "results": results,
                    "response": text_response or "Instruksi berhasil dieksekusi.",
                }
            elif text_response:
                return {
                    "source": "llm_response",
                    "matched": True,
                    "actions": [],
                    "results": [],
                    "response": text_response,
                }

        return {
            "source": "unmatched",
            "matched": False,
            "actions": [],
            "results": [],
            "response": "",
        }

