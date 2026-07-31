import pytest

from locking_Lock import Lock
from locking_LockManager import LockManager
from locking_WaitForGraph import WaitForGraph
from models_Agent import Agent, AgentState


def create_test_agent(agent_id: str) -> Agent:
    """Helper to instantiate an Agent in the RUNNING state for testing."""
    agent = Agent(
        id=agent_id,
        priority=1,
        arrival_time=0,
        operations=[],
    )
    # Fast-forward state to RUNNING to allow valid transitions to BLOCKED
    agent.state = AgentState.READY
    agent.state = AgentState.RUNNING
    return agent


@pytest.fixture
def empty_lock_manager():
    """Provides a fresh LockManager instance."""
    return LockManager()


class TestLockManagerInitialization:
    def test_initialization(self, empty_lock_manager):
        """Standard Case: LockManager initializes with an empty lock tracking structure and a wait-for graph."""
        assert hasattr(empty_lock_manager, "locks")
        assert len(empty_lock_manager.locks) == 0
        assert hasattr(empty_lock_manager, "waitForGraph")
        assert isinstance(empty_lock_manager.waitForGraph, WaitForGraph)


class TestLockManagerAcquire:
    @pytest.mark.parametrize(
        "mode, expected_type",
        [("read", "shared"), ("write", "exclusive"), ("append", "exclusive")],
    )
    def test_acquire_new_lock_creates_correct_type(
        self, empty_lock_manager, mode, expected_type
    ):
        """Standard Case: Acquiring a non-existent lock creates it, sets correct type, and adds holder."""
        agent = create_test_agent("A1")
        path = "/data/file1"

        granted, waiting_on, cycle = empty_lock_manager.acquire(agent, path, mode)

        assert granted is True
        assert waiting_on == []
        assert cycle == []

        assert path in empty_lock_manager.locks

        lock = empty_lock_manager.locks[path]
        assert isinstance(lock, Lock)
        assert lock.type == expected_type
        assert agent in lock.holders
        assert len(lock.waiters) == 0
        assert agent.state == AgentState.RUNNING
        assert len(empty_lock_manager.waitForGraph.edges) == 0

    def test_acquire_existing_shared_lock_with_read(self, empty_lock_manager):
        """Standard Case: Read requests on an existing shared lock are granted immediately."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        # Agent 1 takes shared lock
        empty_lock_manager.acquire(agent1, path, "read")

        # Agent 2 requests read
        granted, waiting_on, cycle = empty_lock_manager.acquire(agent2, path, "read")

        assert granted is True
        assert waiting_on == []
        assert cycle == []

        lock = empty_lock_manager.locks[path]
        assert lock.type == "shared"
        assert agent1 in lock.holders
        assert agent2 in lock.holders
        assert len(lock.waiters) == 0
        assert len(empty_lock_manager.waitForGraph.edges) == 0

    @pytest.mark.parametrize("mode", ["write", "append"])
    def test_acquire_existing_shared_lock_with_write_blocks(
        self, empty_lock_manager, mode
    ):
        """Standard Case: Write/append requests on a shared lock fail, block the agent, queue it, and add graph edges."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        agent3 = create_test_agent("A3")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "read")
        empty_lock_manager.acquire(agent2, path, "read")

        # Agent 3 requests write, must block on both A1 and A2
        granted, waiting_on, cycle = empty_lock_manager.acquire(agent3, path, mode)

        assert granted is False
        assert set(waiting_on) == {"A1", "A2"}
        assert cycle == []

        lock = empty_lock_manager.locks[path]

        # Agent 1 and 2 still hold it
        assert agent1 in lock.holders
        assert agent2 in lock.holders
        assert agent3 not in lock.holders

        # Agent 3 is in waiters and blocked
        assert agent3 in lock.waiters
        assert agent3.state == AgentState.BLOCKED

        # Validate wait-for graph edges exist for A3 -> A1 and A3 -> A2
        edges = empty_lock_manager.waitForGraph.edges
        assert any(
            e.frm == agent3.id and e.to == agent1.id and e.path == path for e in edges
        )
        assert any(
            e.frm == agent3.id and e.to == agent2.id and e.path == path for e in edges
        )

    @pytest.mark.parametrize("mode", ["read", "write", "append"])
    def test_acquire_existing_exclusive_lock_blocks_all(self, empty_lock_manager, mode):
        """Standard Case: Any request on an exclusive lock fails, blocks the agent, queues it, and adds a graph edge."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "write")

        granted, waiting_on, cycle = empty_lock_manager.acquire(agent2, path, mode)

        assert granted is False
        assert waiting_on == ["A1"]
        assert cycle == []

        lock = empty_lock_manager.locks[path]

        assert agent1 in lock.holders
        assert agent2 not in lock.holders
        assert agent2 in lock.waiters
        assert agent2.state == AgentState.BLOCKED

        # Validate wait-for graph edge
        edges = empty_lock_manager.waitForGraph.edges
        assert any(
            e.frm == agent2.id and e.to == agent1.id and e.path == path for e in edges
        )

    def test_acquire_invalid_mode_raises_error(self, empty_lock_manager):
        """Edge Case: Acquiring with an invalid mode should raise a ValueError."""
        agent = create_test_agent("A1")
        with pytest.raises(ValueError):
            empty_lock_manager.acquire(agent, "/data/file1", "delete")

    def test_acquire_deadlock_detected(self, empty_lock_manager):
        """Edge Case: Acquiring a lock that forms a wait cycle must be rejected completely without blocking."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path1 = "/data/file1"
        path2 = "/data/file2"

        # Setup: A1 holds path1, A2 holds path2[cite: 11]
        empty_lock_manager.acquire(agent1, path1, "write")
        empty_lock_manager.acquire(agent2, path2, "write")

        # A1 requests path2 -> Blocks, edge A1 -> A2 added
        granted1, waiting1, cycle1 = empty_lock_manager.acquire(agent1, path2, "read")
        assert granted1 is False
        assert waiting1 == ["A2"]
        assert cycle1 == []
        assert agent1.state == AgentState.BLOCKED

        # A2 requests path1 -> Will cause cycle (A2 waits on A1, A1 waits on A2)
        granted2, waiting2, cycle2 = empty_lock_manager.acquire(agent2, path1, "read")

        # Deadlock handling expectations:
        assert granted2 is False
        assert waiting2 == []
        assert set(cycle2) == {"A1", "A2"}

        # Agent state must remain untouched[cite: 11]
        assert agent2.state == AgentState.RUNNING
        # Agent must not be added to waiters
        lock1 = empty_lock_manager.locks[path1]
        assert agent2 not in lock1.waiters
        # The speculative graph edge must be rolled back[cite: 11]
        edges = empty_lock_manager.waitForGraph.edges
        assert not any(
            e.frm == agent2.id and e.to == agent1.id and e.path == path1 for e in edges
        )


class TestLockManagerRelease:
    def test_release_shared_lock_partial(self, empty_lock_manager):
        """Standard Case: Releasing a shared lock with multiple holders just removes the releasing agent."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        agent3 = create_test_agent("A3")
        path = "/data/file1"

        # Setup: A1 and A2 hold read, A3 is waiting for write[cite: 11]
        empty_lock_manager.acquire(agent1, path, "read")
        empty_lock_manager.acquire(agent2, path, "read")
        empty_lock_manager.acquire(agent3, path, "write")

        lock = empty_lock_manager.locks[path]

        # Action: A1 releases
        woken_agents = empty_lock_manager.release(agent1, path)

        # Assertions
        assert woken_agents == []
        assert agent1 not in lock.holders
        assert agent2 in lock.holders
        assert lock.type == "shared"  # Stays shared

        # A3 is still waiting because A2 holds the lock[cite: 11]
        assert agent3 in lock.waiters
        assert agent3.state == AgentState.BLOCKED
        # Lock should still exist in the dictionary
        assert path in empty_lock_manager.locks

    def test_release_last_holder_wakes_waiters_and_deletes_lock_and_edges(
        self, empty_lock_manager
    ):
        """Standard Case: Releasing the last holder wakes waiters, deletes lock, and purges wait-edges."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        agent3 = create_test_agent("A3")
        path = "/data/file1"

        # Setup: A1 holds write, A2 and A3 are waiting[cite: 11]
        empty_lock_manager.acquire(agent1, path, "write")
        empty_lock_manager.acquire(agent2, path, "read")
        empty_lock_manager.acquire(agent3, path, "write")

        # Verify edges exist before release
        edges_before = empty_lock_manager.waitForGraph.edges
        assert any(e.frm == agent2.id and e.path == path for e in edges_before)
        assert any(e.frm == agent3.id and e.path == path for e in edges_before)

        # Action: A1 releases (the only holder)[cite: 11]
        woken_agents = empty_lock_manager.release(agent1, path)

        # Assertions
        # Woken agents must be explicitly returned
        assert set(woken_agents) == {"A2", "A3"}

        # 1. Woken agents must be READY
        assert agent2.state == AgentState.READY
        assert agent3.state == AgentState.READY

        # 2. The lock must be deleted from the manager
        assert path not in empty_lock_manager.locks

        # 3. Waiter edges for this path must be purged from the graph
        edges_after = empty_lock_manager.waitForGraph.edges
        assert not any(e.frm == agent2.id and e.path == path for e in edges_after)
        assert not any(e.frm == agent3.id and e.path == path for e in edges_after)

    def test_release_non_existent_lock(self, empty_lock_manager):
        """Edge Case: Releasing a lock that does not exist should be handled gracefully."""
        agent = create_test_agent("A1")
        # Should not raise an exception or crash
        woken_agents = empty_lock_manager.release(agent, "/data/ghost_file")
        assert woken_agents == []

    def test_release_agent_not_in_holders(self, empty_lock_manager):
        """Edge Case: Releasing an agent that doesn't actually hold the lock."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "read")

        # Agent 2 tries to release Agent 1's lock[cite: 11]
        woken_agents = empty_lock_manager.release(agent2, path)

        assert woken_agents == []
        lock = empty_lock_manager.locks[path]
        assert agent1 in lock.holders  # A1 still has it
