from locking_Lock import Lock
from locking_WaitForGraph import WaitForGraph
from models_Agent import Agent, AgentState


class LockManager:
    def __init__(self):
        # Maps a string path to a Lock object
        self.locks: dict[str, Lock] = {}
        # Wait-for graph for deadlock detection
        self.waitForGraph = WaitForGraph()

    def acquire(self, agent: Agent, path: str, mode: str) -> bool:
        if mode not in ("read", "write", "append"):
            raise ValueError(
                f"Invalid mode '{mode}'. Must be 'read', 'write', or 'append'."
            )

        requested_type = "shared" if mode == "read" else "exclusive"

        # Case 1: Lock doesn't exist yet
        if path not in self.locks:
            new_lock = Lock(path, requested_type)
            new_lock.holders.append(agent)
            self.locks[path] = new_lock
            return True

        lock = self.locks[path]

        # Case 2: Lock exists and is compatible (Shared + Read)
        if lock.type == "shared" and mode == "read":
            lock.holders.append(agent)
            return True

        # Case 3: Incompatible (Shared + Write/Append OR Exclusive + Anything)
        # Speculatively add edges to the wait-for graph
        added_edges = []
        for holder in lock.holders:
            self.waitForGraph.addEdge(agent.id, holder.id, path)
            added_edges.append((agent.id, holder.id, path))

        # Check for cycles
        if self.waitForGraph.hasCycle(agent.id):
            # Deadlock detected: Roll back speculative edges
            for frm, to, p in added_edges:
                self.waitForGraph.removeEdge(frm, to, p)
            # Reject acquisition completely without blocking
            return False

        # No cycle detected: Safe to wait
        lock.waiters.append(agent)
        agent.state = AgentState.BLOCKED
        return False

    def release(self, agent: Agent, path: str) -> None:
        # Gracefully handle non-existent locks
        if path not in self.locks:
            return

        lock = self.locks[path]

        # Gracefully handle if agent isn't actually holding the lock
        if agent not in lock.holders:
            return

        # Remove the agent from holders
        lock.holders.remove(agent)

        # If the lock is fully free
        if not lock.holders:
            waiter_ids = {w.id for w in lock.waiters}

            # Identify and delete all wait-for edges for the promoted waiters on this path
            edges_to_remove = [
                e
                for e in self.waitForGraph.edges
                if e.path == path and e.frm in waiter_ids
            ]
            for e in edges_to_remove:
                self.waitForGraph.removeEdge(e.frm, e.to, e.path)

            # Wake all waiters
            for waiter in lock.waiters:
                waiter.state = AgentState.READY

            # Delete the lock completely from the manager
            del self.locks[path]
