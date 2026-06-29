from enum import Enum
from pathlib import Path

__all__ = ["TriggerEnum", "RUNTIME_FOLDER", "SERIALIZATION_PERIOD"]

RUNTIME_FOLDER: Path = Path(__file__).parent.parent / "runtime_files"
RUNTIME_FOLDER.mkdir(exist_ok=True)

SERIALIZATION_PERIOD = 600  # 10 minutes

class TriggerEnum(Enum):
    CLI = "Command from user"
    WEB = "Command from Web GUI"
    AGENT_CALL = "Agent tool usage"