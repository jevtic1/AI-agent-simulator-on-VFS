from enum import Enum
from typing import List

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
    # Static list to hold references to all instantiated agents
    all_agents: List["Agent"] = []

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

        # Add the current instance to the static list
        Agent.all_agents.append(self)

    def nextOperation(self):
        if self.current_op_index >= len(self.operations):
            return None
        return self.operations[self.current_op_index]

    def advance(self, vfs, lock_manager):
        result = None

        # Prevent executing past the end of the operations list
        if self.current_op_index < len(self.operations):
            op = self.operations[self.current_op_index]

            # Execute must only be called directly from advance()
            # Forwards the return value from execute()
            result = op.execute(self, vfs, lock_manager)

            # Terminate immediately if an operation returns an ERROR
            if result and result[0] == "ERROR":
                self.state = AgentState.TERMINATED
                return result

            # Only progress to the next operation if the current one has no remaining time
            if op.remaining == 0:
                self.isPreemptible = True
                self.current_op_index += 1

        # Set to TERMINATED if the agent has finished all operations
        if self.current_op_index >= len(self.operations):
            self.state = AgentState.TERMINATED
            if result is None:
                return "ERROR", None, "GRESKA. Agent pozvan nakon svog kraja.", [], None

        return result

    def report_row(self) -> str:
        """Returns the formatted summary row for the agent report matching system output formatting."""
        status_map = {
            AgentState.NEW: "novi",
            AgentState.READY: "spreman",
            AgentState.RUNNING: "izvršava se",
            AgentState.BLOCKED: "blokiran",
            AgentState.TERMINATED: "zavrsen",
        }
        status_str = status_map.get(self.state, self.state.name.lower())
        return f"{self.id:<7} {status_str:<11} {self.arrival_time:<9} {self.start_time:<8} {self.end_time:<5} {self.wait_time:<8} {self.blocked_time:<10} {self.preemption_count:<13}"

    @classmethod
    def clear_agents(cls):
        """Utility method to clear the static list (useful for test isolation)."""
        cls.all_agents.clear()

    @classmethod
    def calculate_average_stats(cls) -> str:
        """Calculates and returns formatted average statistics for all registered agents."""
        if not cls.all_agents:
            return "Prosjecno vrijeme čekanja: 0.00\nProsjecno vrijeme blokiranja: 0.00"

        total_wait_time = sum(agent.wait_time for agent in cls.all_agents)
        total_blocked_time = sum(agent.blocked_time for agent in cls.all_agents)

        avg_wait = total_wait_time / len(cls.all_agents)
        avg_blocked = total_blocked_time / len(cls.all_agents)

        return f"Prosjecno vrijeme čekanja: {avg_wait:.2f}\nProsjecno vrijeme blokiranja: {avg_blocked:.2f}"
