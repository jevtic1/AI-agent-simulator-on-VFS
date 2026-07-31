from dataclasses import dataclass
from typing import Set, Tuple, List


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

    def hasCycle(self, agent_id: str) -> Tuple[bool, List[str]]:
        # Build an adjacency list representing who is waiting on whom
        adj = {}
        for edge in self.edges:
            adj.setdefault(edge.frm, set()).add(edge.to)

        visited = set()
        rec_stack = set()
        path_list = []

        def dfs(current_agent: str) -> Tuple[bool, List[str]]:
            # If we hit an agent currently in the recursion stack, we found a cycle
            if current_agent in rec_stack:
                # Extract only the sequence of agents that form the loop
                cycle_start_index = path_list.index(current_agent)
                return True, path_list[cycle_start_index:]

            # If we hit an already fully processed agent, no cycle down this path
            if current_agent in visited:
                return False, []

            visited.add(current_agent)
            rec_stack.add(current_agent)
            path_list.append(current_agent)

            # Traverse all agents the current agent is waiting on
            for next_agent in adj.get(current_agent, []):
                found, cycle = dfs(next_agent)
                if found:
                    return True, cycle

            # Backtrack
            path_list.pop()
            rec_stack.remove(current_agent)
            return False, []

        return dfs(agent_id)
