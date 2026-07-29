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


class Agent:
    def __init__(
        self,
        id: str,
        priority: int,
        arrival_time: int,
        operations: list,
        isPreemptible: bool = True,
    ):
        if priority < 0:
            raise ValueError("Priority cannot be negative")
        if arrival_time < 0:
            raise ValueError("Arrival time cannot be negative")

        self.id = id
        self.priority = priority
        self.arrival_time = arrival_time
        self.operations = operations

        self.current_op_index = 0
        self.state = AgentState.NEW
        self.start_time = 0
        self.end_time = 0
        self.wait_time = 0
        self.blocked_time = 0
        self.preemption_count = 0
        self.handles = {}
        self.isPreemptible = isPreemptible

    def nextOperation(self):
        if self.current_op_index >= len(self.operations):
            return None
        return self.operations[self.current_op_index]

    def advance(self):
        if self.current_op_index < len(self.operations):
            self.current_op_index += 1

        if self.current_op_index >= len(self.operations):
            self.state = AgentState.TERMINATED
