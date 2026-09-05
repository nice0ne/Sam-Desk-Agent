from typing import List, Dict, Any, Optional


class ToolRegistry:
    """Registry defining OpenAI-compatible JSON function schemas for all available tools."""

    @staticmethod
    def get_schemas() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "launch_application",
                    "description": "Membuka aplikasi Windows dan memfokuskan jendelanya.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Nama aplikasi atau executable, misal 'notepad', 'calc', 'chrome'",
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Argumen opsional untuk aplikasi",
                            },
                        },
                        "required": ["app_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "close_application",
                    "description": "Menutup aplikasi berdasarkan nama jendela atau proses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Nama jendela atau nama file exe",
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Paksa kill proses jika True",
                            },
                        },
                        "required": ["target"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adjust_system_volume",
                    "description": "Menaikkan, menurunkan, atau mengatur volume suara master Windows.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "delta": {
                                "type": "number",
                                "description": "Perubahan volume relatif, misal +0.3 untuk naik 30%, -0.2 untuk turun 20%",
                            },
                            "level": {
                                "type": "number",
                                "description": "Level volume absolut (0.0 sampai 1.0)",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "type_keyboard",
                    "description": "Mengetik teks langsung ke jendela yang aktif.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Teks yang ingin diketik",
                            },
                            "use_clipboard": {
                                "type": "boolean",
                                "description": "Gunakan paste clipboard agar instan",
                            },
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mouse_drag",
                    "description": "Menggerakkan mouse sambil menahan klik (drag-and-drop / menggambar di kanvas Paint).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer", "description": "Koordinat X awal"},
                            "start_y": {"type": "integer", "description": "Koordinat Y awal"},
                            "end_x": {"type": "integer", "description": "Koordinat X akhir"},
                            "end_y": {"type": "integer", "description": "Koordinat Y akhir"},
                            "duration": {"type": "number", "description": "Durasi drag dalam detik"},
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Mencari informasi terkini dari internet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Kata kunci pencarian"},
                            "max_results": {"type": "integer", "description": "Jumlah maksimal hasil pencarian"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "speak_feedback",
                    "description": "Memberikan pesan konfirmasi suara ke pengguna.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Pesan yang diucapkan"},
                        },
                        "required": ["message"],
                    },
                },
            },
        ]

    @classmethod
    def get_tool_names(cls) -> List[str]:
        return [s["function"]["name"] for s in cls.get_schemas() if "function" in s]

    @classmethod
    def get_schema(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        for s in cls.get_schemas():
            if s.get("function", {}).get("name") == tool_name:
                return s
        return None
