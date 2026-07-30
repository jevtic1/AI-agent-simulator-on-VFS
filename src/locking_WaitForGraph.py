from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class Edge:
    frm: str
    to: str
    path: str


class WaitForGraph:
    def __init__(self):
        # Using a set natively prevents duplicates and allows O(1) removals
        self.edges: Set[Edge] = set()

    def addEdge(self, frm: str, to: str, path: str) -> None:
        self.edges.add(Edge(frm, to, path))

    def removeEdge(self, frm: str, to: str, path: str) -> None:
        # discard() removes the item if it exists, and does nothing if it doesn't
        self.edges.discard(Edge(frm, to, path))

    def hasCycle(self, agent_id: str) -> bool:
        # Build an adjacency list representing who is waiting on whom
        adj = {}
        for edge in self.edges:
            adj.setdefault(edge.frm, set()).add(edge.to)

        visited = set()
        rec_stack = set()

        def dfs(current_agent: str) -> bool:
            # If we hit an agent currently in the recursion stack, we found a cycle
            if current_agent in rec_stack:
                return True
            # If we hit an already fully processed agent, no cycle down this path
            if current_agent in visited:
                return False

            visited.add(current_agent)
            rec_stack.add(current_agent)

            # Traverse all agents the current agent is waiting on
            for next_agent in adj.get(current_agent, []):
                if dfs(next_agent):
                    return True

            rec_stack.remove(current_agent)
            return False

        return dfs(agent_id)
