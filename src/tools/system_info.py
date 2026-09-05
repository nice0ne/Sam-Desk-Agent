import platform
import psutil
from typing import Dict, Any


class SystemInfoTool:
    def get_summary(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "os": platform.platform(),
            "cpu_percent": psutil.cpu_percent(0.1),
            "ram_percent": mem.percent,
            "ram_available_gb": round(mem.available / (1024**3), 2)
        }
