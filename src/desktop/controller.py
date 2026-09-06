from typing import Dict, Any, Optional
from src.desktop.os_actions import OSController
from src.desktop.mouse_keyboard import MouseKeyboardController
from src.desktop.uia_actions import UIAController
from src.desktop.vision_actions import VisionController
from src.core.safety import SafetySupervisor


class DesktopActionController:
    """Unified facade for desktop automation layers (OS actions, mouse/keyboard, UIA, vision)."""

    def __init__(self, safety_supervisor: Optional[SafetySupervisor] = None):
        self.safety = safety_supervisor or SafetySupervisor()
        self.os_ctrl = OSController()
        self.mk_ctrl = MouseKeyboardController()
        self.uia_ctrl = UIAController()
        self.vision_ctrl = VisionController()

    def execute_action(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch and execute a desktop automation tool request after verifying safety state."""
        if self.safety.is_cancelled():
            return {"status": "cancelled", "message": "Action execution aborted by safety supervisor."}

        try:
            if tool_name == "launch_application":
                app = params.get("app_name") or params.get("name")
                args = params.get("args", [])
                return self.os_ctrl.launch_app(app, args)

            elif tool_name == "close_application":
                target = params.get("target") or params.get("name")
                force = params.get("force", False)
                res = self.os_ctrl.close_app(target, force)
                return {"status": "success" if res else "not_found", "closed": res}

            elif tool_name == "adjust_system_volume":
                delta = float(params.get("delta", 0.0))
                level = float(params.get("level")) if "level" in params and params["level"] is not None else None
                new_vol = self.os_ctrl.adjust_volume(delta, level)
                return {"status": "success", "level": new_vol}

            elif tool_name == "focus_window":
                pattern = params.get("title_pattern") or params.get("title")
                res = self.os_ctrl.focus_window(pattern)
                return {"status": "success" if res else "not_found", "focused": res}

            elif tool_name == "mouse_click":
                x = int(params["x"])
                y = int(params["y"])
                btn = params.get("button", "left")
                self.mk_ctrl.click(x, y, btn)
                return {"status": "success", "action": "click", "x": x, "y": y}

            elif tool_name == "mouse_drag":
                start_x = int(params["start_x"])
                start_y = int(params["start_y"])
                end_x = int(params["end_x"])
                end_y = int(params["end_y"])
                if "duration" in params:
                    self.mk_ctrl.drag(start_x, start_y, end_x, end_y, duration=float(params["duration"]))
                else:
                    self.mk_ctrl.drag(start_x, start_y, end_x, end_y)
                return {"status": "success", "action": "drag"}

            elif tool_name == "type_keyboard":
                text = params.get("text", "")
                use_clipboard = params.get("use_clipboard", False)
                self.mk_ctrl.type_text(text, use_clipboard)
                return {"status": "success", "typed_length": len(text)}

            elif tool_name == "press_hotkey":
                keys = params.get("keys", [])
                self.mk_ctrl.hotkey(keys)
                return {"status": "success", "hotkey": keys}

            elif tool_name == "click_ui_element":
                name = params.get("name", "")
                res = self.uia_ctrl.click_element_by_name(name)
                return {"status": "success" if res else "not_found", "clicked": res}

            elif tool_name in ("speak_feedback", "speak"):
                msg = params.get("message") or params.get("text") or ""
                return {"status": "success", "message": msg}

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
