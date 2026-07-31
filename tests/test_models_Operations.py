import pytest

# Concrete Implementations
from locking_LockManager import LockManager
from logger_Event import EventType
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
from vfs_FileHandle import FileHandle


@pytest.fixture
def agent():
    created_agent = Agent(
        id="agent_1", priority=1, arrival_time=0, operations=[], isPreemptible=True
    )
    created_agent.state = AgentState.RUNNING
    return created_agent


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

    def test_think_op_execution_running(self, agent, vfs, lock_manager):
        op = ThinkOp(duration=5)

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "RUNNING"
        assert event_type == EventType.THINKING
        assert detail == "agent_1 THINKING\n"
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 4

    def test_think_op_execution_done(self, agent, vfs, lock_manager):
        op = ThinkOp(duration=1)

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.THINK_DONE
        assert detail == "agent_1 THINKING\nagent_1 FINISHED THINKING\n"
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 0


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
        # Initialization still throws exceptions
        with pytest.raises((ValueError, TypeError)):
            OpenOp(path=path, mode=mode, handle=handle)

    def test_open_op_successful_execute(self, agent, vfs, lock_manager):
        """Standard Case: Lock acquired successfully. Creates handle and returns DONE."""
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.OPEN_GRANTED
        assert detail == "agent_1 OPEN /tmp/test.txt write as h100 -> zakljucano\n"
        assert related == []
        assert path == "/tmp/test.txt"

        assert agent.isPreemptible is False
        assert op.remaining == 0
        assert "/tmp/test.txt" in lock_manager.locks

        assert "h100" in agent.handles
        created_handle = agent.handles["h100"]
        assert created_handle.id == "h100"
        assert created_handle.path == "/tmp/test.txt"
        assert created_handle.mode == "write"
        assert created_handle.agentId == agent.id

    def test_open_op_failed_execute_blocks(self, agent, vfs, lock_manager):
        """Standard Case: Lock acquire returns False. Blocks agent, returns BLOCKED."""
        agent2 = Agent(id="agent_2", priority=1, arrival_time=0, operations=[])
        lock_manager.acquire(agent2, "/tmp/test.txt", "write")

        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "BLOCKED"
        assert event_type == EventType.OPEN_BLOCKED
        assert (
            detail
            == "agent_1 OPEN /tmp/test.txt write as h100 -> blokiran, ceka agent_2\n"
        )
        assert related == ["agent_2"]
        assert path == "/tmp/test.txt"

        assert agent.isPreemptible is False
        assert "h100" not in agent.handles
        assert op.remaining == 1
        assert agent.state == AgentState.BLOCKED
        assert agent in lock_manager.locks["/tmp/test.txt"].waiters

    def test_open_op_failed_execute_rejects(self, agent, vfs, lock_manager):
        """Standard Case: Lock acquire detects cycle, returns REJECTED."""
        agent2 = Agent(id="agent_2", priority=1, arrival_time=0, operations=[])

        # Setup cycle
        lock_manager.acquire(agent, "/docs/readme.txt", "write")
        lock_manager.acquire(agent2, "/tmp/test.txt", "write")
        lock_manager.acquire(
            agent2, "/docs/readme.txt", "write"
        )  # agent2 waits on agent1

        # agent1 attempts to acquire what agent2 holds -> cycle
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "REJECTED"
        assert event_type == EventType.OPEN_REJECTED
        assert "odbijeno, nastao bi ciklus" in detail
        assert agent2.id in detail
        assert related != []
        assert path == "/tmp/test.txt"

        assert agent.isPreemptible is False
        assert "h100" not in agent.handles

        assert op.remaining == 1
        assert agent.state == AgentState.RUNNING
        assert agent not in lock_manager.locks["/tmp/test.txt"].waiters

    def test_open_op_execution_error(self, agent, lock_manager):
        """Edge Case: Ensure unexpected errors during execution are caught and returned as an ERROR tuple."""
        # Using an invalid VFS object intentionally to trigger an internal error inside execute()
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        status, event_type, detail, related, path = op.execute(
            agent, None, lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.OPEN_ERROR
        assert (
            detail
            == "agent_1 OPEN /tmp/test.txt write as h100 -> GRESKA: desila se nepredvidjena greska\n"
        )
        assert path == "/tmp/test.txt"

        assert agent.isPreemptible is False
        assert "h100" not in agent.handles

        assert op.remaining == 1
        assert agent.state == AgentState.RUNNING


class TestReadOp:
    def test_read_op_initialization(self):
        op = ReadOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_read_op_invalid_handle(self):
        with pytest.raises(ValueError):
            ReadOp(handle="")

    def test_read_op_execution_success(self, agent, vfs, lock_manager):
        agent.handles["h1"] = FileHandle(
            id="h1", path="/docs/readme.txt", mode="ro", agentId=agent.id
        )
        op = ReadOp(handle="h1")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.READ_DONE
        assert detail == "agent_1 READ h1. Output: read-only content\n"
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 0

    def test_read_op_execution_fails_missing_handle(self, agent, vfs, lock_manager):
        """Edge Case: Missing handle throws internally, caught and mapped to ERROR tuple."""
        op = ReadOp(handle="missing_h")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "ERROR"
        assert event_type == EventType.READ_ERROR
        assert (
            detail
            == "agent_1 READ missing_h -> GRESKA: desila se nepredvidjena greska\n"
        )
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 1


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

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.WRITE_DONE
        assert detail == "agent_1 WRITE h_write 'Completely overwritten data.'\n"
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 0
        assert vfs.resolve("/docs/data.txt").read() == "Completely overwritten data."

    def test_write_op_fails_if_invalid_mode(self, agent, vfs, lock_manager):

        agent.handles["h_write"] = FileHandle(
            id="h_write", path="/docs/readme.txt", mode="ro", agentId=agent.id
        )
        op = WriteOp(handle="h_write", data="Should not write")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "ERROR"
        assert event_type == EventType.WRITE_ERROR
        assert (
            detail
            == "agent_1 WRITE h_write 'Should not write' -> GRESKA: desila se nepredvidjena greska\n"
        )
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 1


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

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.APPEND_DONE
        assert detail == "agent_1 APPEND h_append 'line 2'\n"
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 0
        assert vfs.resolve("/docs/log.txt").read() == "line 1\nline 2"

    def test_append_op_fails_if_invalid_mode(self, agent, vfs, lock_manager):
        agent.handles["h_append"] = FileHandle(
            id="h_append", path="/docs/readme.txt", mode="ro", agentId=agent.id
        )
        op = AppendOp(handle="h_append", data="line 2")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "ERROR"
        assert event_type == EventType.APPEND_ERROR
        assert (
            detail
            == "agent_1 APPEND h_append 'line 2' -> GRESKA: desila se nepredvidjena greska\n"
        )
        assert related == []
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 1


class TestCloseOp:
    def test_close_op_initialization(self):
        op = CloseOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_close_op_invalid_handle_init(self):
        with pytest.raises((ValueError, KeyError)):
            CloseOp(handle="invalid_handle")

    def test_close_op_execution_success(self, agent, vfs, lock_manager):
        lock_manager.acquire(agent, "/docs/close_me.txt", "write")
        agent.handles["h_close"] = FileHandle(
            id="h_close", path="/docs/close_me.txt", mode="rw", agentId=agent.id
        )
        op = CloseOp(handle="h_close")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "DONE"
        assert event_type == EventType.CLOSE_DONE
        assert detail == "CLOSE h_close\n"
        assert related == []  # Since no agents were woken in this test scenario
        assert path == "/docs/close_me.txt"

        assert agent.isPreemptible is False
        assert op.remaining == 0
        assert "h_close" not in agent.handles
        assert "/docs/close_me.txt" not in lock_manager.locks

    def test_close_op_execution_fails_missing_handle(self, agent, vfs, lock_manager):
        op = CloseOp(handle="missing_h")

        status, event_type, detail, related, path = op.execute(agent, vfs, lock_manager)

        assert status == "ERROR"
        assert event_type == EventType.CLOSE_ERROR
        assert detail == "CLOSE missing_h\n -> GRESKA: desila se nepredvidjena greska\n"
        # Path is unresolvable when the handle is missing
        assert path is None

        assert agent.isPreemptible is False
        assert op.remaining == 1


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        with pytest.raises(TypeError):
            Operation(remaining=1)
