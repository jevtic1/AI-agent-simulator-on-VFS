import pytest

# Concrete Implementations
from locking_LockManager import LockManager
from models_Agent import Agent, AgentState
from models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    Operation,
    ReadOp,
    ThinkOp,
    WriteOp,
)
from src.vfs_VFile import VFile
from src.vfs_VFS import VFS
from vfs_FileHandle import (
    FileHandle,
)  # Assuming standard location based on common patterns


@pytest.fixture
def agent():
    return Agent(
        id="agent_1", priority=1, arrival_time=0, operations=[], isPreemptible=True
    )


@pytest.fixture
def vfs():
    vfs_instance = VFS()
    # Populate the VFS with concrete VFiles manually to avoid local disk dependency during testing
    vfs_instance.files.append(VFile(path="/tmp/test.txt", content="", mode="rw"))
    vfs_instance.files.append(
        VFile(path="/docs/readme.txt", content="read-only content", mode="ro")
    )
    vfs_instance.files.append(
        VFile(path="/docs/data.txt", content="initial content", mode="rw")
    )
    vfs_instance.files.append(
        VFile(path="/docs/log.txt", content="line 1\n", mode="rw")
    )
    vfs_instance.files.append(VFile(path="/docs/close_me.txt", content="", mode="rw"))
    return vfs_instance


@pytest.fixture
def lock_manager():
    return LockManager()


class TestThinkOp:
    def test_think_op_initialization(self):
        op = ThinkOp(duration=5)
        assert op.duration == 5
        assert op.remaining == 5

    @pytest.mark.parametrize("invalid_duration", [0, -1, -100])
    def test_think_op_invalid_duration(self, invalid_duration):
        with pytest.raises(ValueError):
            ThinkOp(duration=invalid_duration)

    def test_think_op_execution(self, agent, vfs, lock_manager):
        op = ThinkOp(duration=5)
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1


class TestOpenOp:
    def test_open_op_initialization(self):
        op = OpenOp(path="/file.txt", mode="r", handle="h1")
        assert op.path == "/file.txt"
        assert op.mode == "r"
        assert op.handle == "h1"
        assert op.remaining == 1

    @pytest.mark.parametrize(
        "path, mode, handle",
        [
            ("", "r", "h1"),
            ("/path", "", "h1"),
            ("/path", "r", ""),
            (None, "r", "h1"),
        ],
    )
    def test_open_op_invalid_arguments(self, path, mode, handle):
        with pytest.raises((ValueError, TypeError)):
            OpenOp(path=path, mode=mode, handle=handle)

    def test_open_op_successful_execute(self, agent, vfs, lock_manager):
        """Standard Case: Lock acquired successfully. Creates handle and decrements remaining."""
        # Using "write" mode or "append" to align with LockManager requirements
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1

        # Verify handle was created and stored in agent table with valid configurations
        assert "h100" in agent.handles
        created_handle = agent.handles["h100"]

        assert created_handle.path == "/tmp/test.txt"
        assert created_handle.mode in ("ro", "rw")
        assert "/tmp/test.txt" in lock_manager.locks

    def test_open_op_failed_execute_blocks(self, agent, vfs, lock_manager):
        """Standard Case: Lock acquire returns False. Blocks agent, wait for next tick."""
        # Introduce a conflicting agent that already holds the lock exclusively
        agent2 = Agent(id="agent_2", priority=1, arrival_time=0, operations=[])
        lock_manager.acquire(agent2, "/tmp/test.txt", "write")

        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False

        # Verify the handle was NOT created because it blocked
        assert "h100" not in agent.handles

        # Verify remaining was NOT decremented (operation is incomplete)
        assert op.remaining == initial_remaining

        # Verify the agent's state transitioned to BLOCKED due to incompatibility
        assert agent.state == AgentState.BLOCKED
        assert agent in lock_manager.locks["/tmp/test.txt"].waiters


class TestReadOp:
    def test_read_op_initialization(self):
        op = ReadOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_read_op_invalid_handle(self):
        with pytest.raises(ValueError):
            ReadOp(handle="")

    def test_read_op_execution_success(self, agent, vfs, lock_manager):
        # Provide concrete FileHandle mapped to a concrete Read-Only VFile
        agent.handles["h1"] = FileHandle(
            id="h1", path="/docs/readme.txt", mode="ro", agentId=agent.id
        )
        op = ReadOp(handle="h1")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1

    def test_read_op_execution_fails_missing_handle(self, agent, vfs, lock_manager):
        op = ReadOp(handle="missing_h")
        initial_remaining = op.remaining

        with pytest.raises((KeyError, ValueError, AttributeError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        # Remaining should not decrement on failure
        assert op.remaining == initial_remaining


class TestWriteOp:
    def test_write_op_initialization(self):
        op = WriteOp(handle="h1", data="Hello World")
        assert op.handle == "h1"
        assert op.data == "Hello World"
        assert op.remaining == 1

    def test_write_op_empty_data_allowed(self):
        op = WriteOp(handle="h1", data="")
        assert op.data == ""

    def test_write_op_execution_success(self, agent, vfs, lock_manager):
        agent.handles["h_write"] = FileHandle(
            id="h_write", path="/docs/data.txt", mode="rw", agentId=agent.id
        )

        op = WriteOp(handle="h_write", data="Completely overwritten data.")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1
        # Must verify the file string was properly overwritten natively via VFS resolution
        assert vfs.resolve("/docs/data.txt").read() == "Completely overwritten data."

    def test_write_op_fails_if_invalid_mode(self, agent, vfs, lock_manager):
        # Simulate a handle mapped in Read-Only mode attempting a write
        agent.handles["h_write"] = FileHandle(
            id="h_write", path="/docs/data.txt", mode="ro", agentId=agent.id
        )

        op = WriteOp(handle="h_write", data="Should not write")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining  # Check no decrement on fail

    def test_write_op_fails_if_mount_readonly(self, agent, vfs, lock_manager):
        # Target a VFile initialized directly in read-only mode, regardless of agent's handle permissions
        agent.handles["h_write"] = FileHandle(
            id="h_write", path="/docs/readme.txt", mode="rw", agentId=agent.id
        )

        op = WriteOp(handle="h_write", data="Should not write")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining


class TestAppendOp:
    def test_append_op_initialization(self):
        op = AppendOp(handle="h2", data="\nNew Line")
        assert op.handle == "h2"
        assert op.data == "\nNew Line"
        assert op.remaining == 1

    def test_append_op_execution_success(self, agent, vfs, lock_manager):
        agent.handles["h_append"] = FileHandle(
            id="h_append", path="/docs/log.txt", mode="rw", agentId=agent.id
        )

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1
        # Must verify the file string was properly appended to existing data
        assert vfs.resolve("/docs/log.txt").read() == "line 1\nline 2"

    def test_append_op_fails_if_invalid_mode(self, agent, vfs, lock_manager):
        agent.handles["h_append"] = FileHandle(
            id="h_append", path="/docs/log.txt", mode="ro", agentId=agent.id
        )

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining

    def test_append_op_fails_if_mount_readonly(self, agent, vfs, lock_manager):
        agent.handles["h_append"] = FileHandle(
            id="h_append", path="/docs/readme.txt", mode="rw", agentId=agent.id
        )

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining


class TestCloseOp:
    def test_close_op_initialization(self):
        op = CloseOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_close_op_invalid_handle_init(self):
        with pytest.raises((ValueError, KeyError)):
            CloseOp(handle="invalid_handle")

    def test_close_op_execution_success(self, agent, vfs, lock_manager):
        """Standard Case: Releasing lock successfully. Lock manager called, handle removed."""
        # Setup lock requirement
        lock_manager.acquire(agent, "/docs/close_me.txt", "write")

        agent.handles["h_close"] = FileHandle(
            id="h_close", path="/docs/close_me.txt", mode="rw", agentId=agent.id
        )
        op = CloseOp(handle="h_close")
        initial_remaining = op.remaining

        op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1

        # Verify handle was removed from agent logic
        assert "h_close" not in agent.handles

        # Verify LockManager actively removed the fully freed lock
        assert "/docs/close_me.txt" not in lock_manager.locks

    def test_close_op_execution_fails_missing_handle(self, agent, vfs, lock_manager):
        op = CloseOp(handle="missing_h")
        initial_remaining = op.remaining

        with pytest.raises((KeyError, ValueError, AttributeError)):
            op.execute(agent, vfs, lock_manager)

        assert agent.isPreemptible is False
        assert op.remaining == initial_remaining - 1


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        with pytest.raises(TypeError):
            Operation(remaining=1)
