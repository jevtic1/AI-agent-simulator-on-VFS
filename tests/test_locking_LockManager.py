import pytest

from locking_Lock import Lock
from locking_LockManager import LockManager
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
        """Standard Case: LockManager initializes with an empty lock tracking structure."""
        assert hasattr(empty_lock_manager, "locks")
        assert len(empty_lock_manager.locks) == 0

    def test_no_wait_for_graph(self, empty_lock_manager):
        """Constraint: LockManager must NOT have a waitForGraph attribute for now."""
        assert not hasattr(empty_lock_manager, "waitForGraph")


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

        result = empty_lock_manager.acquire(agent, path, mode)

        assert result is True
        assert path in empty_lock_manager.locks

        lock = empty_lock_manager.locks[path]
        assert isinstance(lock, Lock)
        assert lock.type == expected_type
        assert agent in lock.holders
        assert len(lock.waiters) == 0
        assert agent.state == AgentState.RUNNING

    def test_acquire_existing_shared_lock_with_read(self, empty_lock_manager):
        """Standard Case: Read requests on an existing shared lock are granted immediately."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        # Agent 1 takes shared lock
        empty_lock_manager.acquire(agent1, path, "read")

        # Agent 2 requests read
        result = empty_lock_manager.acquire(agent2, path, "read")

        assert result is True
        lock = empty_lock_manager.locks[path]
        assert lock.type == "shared"
        assert agent1 in lock.holders
        assert agent2 in lock.holders
        assert len(lock.waiters) == 0

    @pytest.mark.parametrize("mode", ["write", "append"])
    def test_acquire_existing_shared_lock_with_write_blocks(
        self, empty_lock_manager, mode
    ):
        """Standard Case: Write/append requests on a shared lock fail, block the agent, and queue it."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "read")

        result = empty_lock_manager.acquire(agent2, path, mode)

        assert result is False
        lock = empty_lock_manager.locks[path]

        # Agent 1 still holds it
        assert agent1 in lock.holders
        assert agent2 not in lock.holders

        # Agent 2 is in waiters and blocked
        assert agent2 in lock.waiters
        assert agent2.state == AgentState.BLOCKED

    @pytest.mark.parametrize("mode", ["read", "write", "append"])
    def test_acquire_existing_exclusive_lock_blocks_all(self, empty_lock_manager, mode):
        """Standard Case: Any request on an exclusive lock fails, blocks the agent, and queues it."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "write")

        result = empty_lock_manager.acquire(agent2, path, mode)

        assert result is False
        lock = empty_lock_manager.locks[path]

        assert agent1 in lock.holders
        assert agent2 not in lock.holders
        assert agent2 in lock.waiters
        assert agent2.state == AgentState.BLOCKED

    def test_acquire_invalid_mode_raises_error(self, empty_lock_manager):
        """Edge Case: Acquiring with an invalid mode should raise a ValueError."""
        agent = create_test_agent("A1")
        with pytest.raises(ValueError):
            empty_lock_manager.acquire(agent, "/data/file1", "delete")


class TestLockManagerRelease:
    def test_release_shared_lock_partial(self, empty_lock_manager):
        """Standard Case: Releasing a shared lock with multiple holders just removes the releasing agent."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        agent3 = create_test_agent("A3")
        path = "/data/file1"

        # Setup: A1 and A2 hold read, A3 is waiting for write
        empty_lock_manager.acquire(agent1, path, "read")
        empty_lock_manager.acquire(agent2, path, "read")
        empty_lock_manager.acquire(agent3, path, "write")

        lock = empty_lock_manager.locks[path]

        # Action: A1 releases
        empty_lock_manager.release(agent1, path)

        # Assertions
        assert agent1 not in lock.holders
        assert agent2 in lock.holders
        assert lock.type == "shared"  # Stays shared

        # A3 is still waiting because A2 holds the lock
        assert agent3 in lock.waiters
        assert agent3.state == AgentState.BLOCKED
        # Lock should still exist in the dictionary
        assert path in empty_lock_manager.locks

    def test_release_last_holder_wakes_waiters_and_deletes_lock(
        self, empty_lock_manager
    ):
        """Standard Case: Releasing the last holder wakes waiters and completely deletes the lock."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        agent3 = create_test_agent("A3")
        path = "/data/file1"

        # Setup: A1 holds write, A2 and A3 are waiting
        empty_lock_manager.acquire(agent1, path, "write")
        empty_lock_manager.acquire(agent2, path, "read")
        empty_lock_manager.acquire(agent3, path, "write")

        # Action: A1 releases (the only holder)
        empty_lock_manager.release(agent1, path)

        # Assertions
        # 1. Woken agents must be READY
        assert agent2.state == AgentState.READY
        assert agent3.state == AgentState.READY

        # 2. The lock must be deleted from the manager
        assert path not in empty_lock_manager.locks

    def test_release_non_existent_lock(self, empty_lock_manager):
        """Edge Case: Releasing a lock that does not exist should be handled gracefully."""
        agent = create_test_agent("A1")
        # Should not raise an exception or crash
        empty_lock_manager.release(agent, "/data/ghost_file")

    def test_release_agent_not_in_holders(self, empty_lock_manager):
        """Edge Case: Releasing an agent that doesn't actually hold the lock."""
        agent1 = create_test_agent("A1")
        agent2 = create_test_agent("A2")
        path = "/data/file1"

        empty_lock_manager.acquire(agent1, path, "read")

        # Agent 2 tries to release Agent 1's lock
        empty_lock_manager.release(agent2, path)

        lock = empty_lock_manager.locks[path]
        assert agent1 in lock.holders  # A1 still has it
