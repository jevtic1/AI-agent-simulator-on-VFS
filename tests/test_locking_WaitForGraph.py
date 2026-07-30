from dataclasses import FrozenInstanceError

import pytest
from locking_WaitForGraph import Edge, WaitForGraph


class TestEdge:
    def test_edge_initialization(self):
        """Test that the Edge data class initializes correctly."""
        edge = Edge(frm="AgentA", to="AgentB", path="/resource/1")
        assert edge.frm == "AgentA"
        assert edge.to == "AgentB"
        assert edge.path == "/resource/1"

    def test_edge_is_frozen(self):
        """Test that the Edge data class is immutable (frozen)."""
        edge = Edge(frm="AgentA", to="AgentB", path="/resource/1")
        with pytest.raises(FrozenInstanceError):
            edge.frm = "AgentC"


class TestWaitForGraph:
    @pytest.fixture
    def graph(self):
        """Fixture to provide a fresh WaitForGraph instance for each test."""
        return WaitForGraph()

    # --- Test addEdge and removeEdge ---

    def test_initialization(self, graph):
        """Test that a new graph has no edges."""
        assert len(graph.edges) == 0

    def test_add_edge(self, graph):
        """Test adding a single edge to the graph."""
        graph.addEdge("A", "B", "/path/1")
        assert len(graph.edges) == 1

        # Depending on implementation, graph.edges could be a list or a set.
        # Convert to list to safely index for the assertion.
        edges_list = list(graph.edges)
        assert edges_list[0].frm == "A"
        assert edges_list[0].to == "B"
        assert edges_list[0].path == "/path/1"

    def test_add_duplicate_edge_ignored(self, graph):
        """Test that adding the exact same edge multiple times is not allowed (idempotent)."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("A", "B", "/path/1")

        # Duplicates must not be allowed
        assert len(graph.edges) == 1

    def test_add_multiple_unique_edges(self, graph):
        """Test adding different edges between the same or different agents."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("A", "B", "/path/2")  # Same agents, different path
        graph.addEdge("A", "C", "/path/1")  # Different target

        assert len(graph.edges) == 3

    def test_remove_edge_existing(self, graph):
        """Test removing an existing edge."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("A", "C", "/path/2")
        graph.removeEdge("A", "B", "/path/1")

        assert len(graph.edges) == 1
        edges_list = list(graph.edges)
        assert edges_list[0].to == "C"

    def test_remove_edge_non_existent(self, graph):
        """Test removing an edge that doesn't exist (should not crash or alter graph)."""
        graph.addEdge("A", "B", "/path/1")
        try:
            graph.removeEdge("A", "B", "/path/2")  # wrong path
            graph.removeEdge("X", "Y", "/path/1")  # wrong agents
        except Exception as e:
            pytest.fail(f"Removing a non-existent edge raised an exception: {e}")

        assert len(graph.edges) == 1

    # --- Test hasCycle (Single Argument) ---

    def test_has_cycle_empty_graph(self, graph):
        """An empty graph cannot have a cycle."""
        assert graph.hasCycle("A") is False

    def test_has_cycle_single_edge(self, graph):
        """A graph with one standard edge has no cycle."""
        graph.addEdge("A", "B", "/path/1")
        assert graph.hasCycle("A") is False
        assert graph.hasCycle("B") is False

    def test_has_cycle_self_loop(self, graph):
        """A self-loop (agent waiting on itself) is an immediate cycle."""
        graph.addEdge("A", "A", "/path/1")
        assert graph.hasCycle("A") is True

    def test_has_cycle_mutual_wait(self, graph):
        """Two agents waiting on each other creates a cycle (Deadlock)."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("B", "A", "/path/2")
        assert graph.hasCycle("A") is True
        assert graph.hasCycle("B") is True

    def test_has_cycle_transitive_no_cycle(self, graph):
        """Three agents in a line (A -> B -> C) has no cycle."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("B", "C", "/path/2")
        assert graph.hasCycle("A") is False
        assert graph.hasCycle("B") is False
        assert graph.hasCycle("C") is False

    def test_has_cycle_triangle_deadlock(self, graph):
        """Three agents waiting in a circle (A -> B -> C -> A) creates a cycle."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("B", "C", "/path/2")
        graph.addEdge("C", "A", "/path/3")

        assert graph.hasCycle("A") is True
        assert graph.hasCycle("B") is True
        assert graph.hasCycle("C") is True

    def test_has_cycle_reachable_cycle(self, graph):
        """An agent outside the cycle that waits on an agent inside the cycle should detect a deadlock."""
        # Cycle between B and C
        graph.addEdge("B", "C", "/path/1")
        graph.addEdge("C", "B", "/path/2")
        # A is waiting on B, so A is blocked by the deadlock
        graph.addEdge("A", "B", "/path/3")

        assert graph.hasCycle("A") is True
        assert graph.hasCycle("B") is True
        assert graph.hasCycle("C") is True

    def test_has_cycle_disconnected_agent(self, graph):
        """Checking an agent not present in the graph should return False."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("B", "A", "/path/2")  # A and B are deadlocked

        assert graph.hasCycle("C") is False  # C is not involved

    def test_has_cycle_removed_cycle(self, graph):
        """Adding a cycle, then removing an edge should resolve the deadlock."""
        graph.addEdge("A", "B", "/path/1")
        graph.addEdge("B", "A", "/path/2")
        assert graph.hasCycle("A") is True

        # Deadlock resolved
        graph.removeEdge("B", "A", "/path/2")
        assert graph.hasCycle("A") is False
        assert graph.hasCycle("B") is False
