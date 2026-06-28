from enum import Enum

__all__ = ["PlatformEnum", "TriggerEnum"]

class PlatformEnum(Enum):
    DISCORD = "Discord"
    WEB = "Web interface"
    SYSTEM = "System"

class TriggerEnum(Enum):
    CLI = "Command from user"
    AGENT_CALL = "Agent tool usage"