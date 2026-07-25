from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    AGENT_ARRIVED = auto()
    SLOT_ASSIGNED = auto()
    SLOT_FREED = auto()
    PREEMPTED = auto()
    OPEN_GRANTED = auto()
    OPEN_BLOCKED = auto()
    OPEN_REJECTED = auto()
    LOCK_RELEASED = auto()
    OPERATION_DONE = auto()
    AGENT_TERMINATED = auto()


@dataclass(frozen=True)
class Event:
    time: int
    type: EventType
    agent_id: str
    detail: str
    related_agent_id: str | None = None
    path: str | None = None

    def __post_init__(self):
        # Validate time (must be non-negative integer, strict check to exclude booleans)
        if (
            not isinstance(self.time, int)
            or isinstance(self.time, bool)
            or self.time < 0
        ):
            raise ValueError("time must be a non-negative integer.")

        # Validate type (must be an EventType enum member)
        if not isinstance(self.type, EventType):
            raise TypeError("type must be a valid EventType.")

        # Validate agent_id (must be non-empty string)
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string.")

        # Validate detail (must be a string, empty strings are allowed)
        if not isinstance(self.detail, str):
            raise TypeError("detail must be a string.")

        # Validate related_agent_id (must be None or non-empty string)
        if self.related_agent_id is not None:
            if (
                not isinstance(self.related_agent_id, str)
                or not self.related_agent_id.strip()
            ):
                raise ValueError("related_agent_id must be None or a non-empty string.")

        # Validate path (must be None or start with '/')
        if self.path is not None:
            if not isinstance(self.path, str) or not self.path.startswith("/"):
                raise ValueError(
                    "path must be None or an absolute path starting with '/'."
                )
