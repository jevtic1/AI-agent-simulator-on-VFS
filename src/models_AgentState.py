from enum import Enum

_VALID_TRANSITIONS = {
    ("NEW", "READY"),
    ("READY", "RUNNING"),
    ("RUNNING", "READY"),
    ("RUNNING", "BLOCKED"),
    ("RUNNING", "TERMINATED"),
    ("BLOCKED", "READY"),
}


class AgentState(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"

    @classmethod
    def is_valid_transition(cls, frm: "AgentState", to: "AgentState") -> bool:
        if not isinstance(frm, cls) or not isinstance(to, cls):
            raise TypeError("frm and to must both be AgentState members")
        return (frm.name, to.name) in _VALID_TRANSITIONS
