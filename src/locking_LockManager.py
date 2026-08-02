from typing import List, Tuple

from src.locking_Lock import Lock
from src.locking_WaitForGraph import WaitForGraph
from src.models_Agent import Agent, AgentState


class LockManager:
    def __init__(self):
        self.locks = {}
        self.waitForGraph = WaitForGraph()

    def acquire(
        self, agent: Agent, path: str, mode: str
    ) -> Tuple[bool, List[str], List[str]]:
        if mode not in ["read", "write", "append"]:
            raise ValueError(f"Invalid mode: {mode}")

        expected_type = "shared" if mode == "read" else "exclusive"

        if path not in self.locks:
            # Initialize Lock with 'path' and 'type', then append the agent
            new_lock = Lock(path=path, type=expected_type)
            new_lock.holders.append(agent)
            self.locks[path] = new_lock
            return True, [], []

        lock = self.locks[path]

        if expected_type == "shared" and lock.type == "shared":
            if agent not in lock.holders:
                lock.holders.append(agent)
            return True, [], []

        for holder in lock.holders:
            self.waitForGraph.addEdge(agent.id, holder.id, path)

        # Check for wait cycles
        has_cycle, cycle_path = self.waitForGraph.hasCycle(agent.id)

        if has_cycle:
            for holder in lock.holders:
                self.waitForGraph.removeEdge(agent.id, holder.id, path)
            return False, [], cycle_path

        agent.state = AgentState.BLOCKED
        if agent not in lock.waiters:
            lock.waiters.append(agent)

        waiting_on = [holder.id for holder in lock.holders]
        return False, waiting_on, []

    def release(self, agent: Agent, path: str) -> List[str]:
        if path not in self.locks:
            return []

        lock = self.locks[path]

        if agent not in lock.holders:
            return []

        lock.holders.remove(agent)

        if len(lock.holders) > 0:
            return []

        woken_agents = []
        for waiter in lock.waiters:
            waiter.state = AgentState.READY
            woken_agents.append(waiter.id)

        edges_to_remove = [e for e in self.waitForGraph.edges if e.path == path]
        for edge in edges_to_remove:
            self.waitForGraph.removeEdge(edge.frm, edge.to, edge.path)

        del self.locks[path]

        return woken_agents
