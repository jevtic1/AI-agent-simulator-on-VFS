from unittest.mock import MagicMock

import pytest

from src.logger_Event import EventType
from src.models_Agent import Agent, AgentState
from src.models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    Operation,
    ReadOp,
    ThinkOp,
    WriteOp,
)
from src.vfs_FileHandle import FileHandle
from src.vfs_VFile import VFile

# Concrete Implementations
from src.vfs_VFS import VFS


@pytest.fixture
def mock_agent_factory():
    """Helper fixture to create mocked Agents."""

    def _create_agent(agent_id="mock_agent"):
        agent = MagicMock(spec=Agent)
        agent.id = agent_id
        agent.state = AgentState.RUNNING
        agent.handles = {}
        return agent

    return _create_agent


@pytest.fixture
def mock_vfile_factory():
    def _create_vfile(path, content, mode):
        mocked_vfile = MagicMock(spec=VFile)
        mocked_vfile.__class__ = VFile

        mocked_vfile.path = path
        mocked_vfile.content = content
        mocked_vfile.mode = mode

        def _read():
            return mocked_vfile.content

        def _write(data):
            if mocked_vfile.mode == "ro":
                raise PermissionError("Cannot write to read-only file")
            mocked_vfile.content = data

        def _append(data):
            if mocked_vfile.mode == "ro":
                raise PermissionError("Cannot append to read-only file")
            mocked_vfile.content += data

        mocked_vfile.read.side_effect = _read
        mocked_vfile.write.side_effect = _write
        mocked_vfile.append.side_effect = _append

        return mocked_vfile

    return _create_vfile


@pytest.fixture
def mock_vfs(mock_vfile_factory):
    mocked_vfs = MagicMock(spec=VFS)
    mocked_vfs.__class__ = VFS

    mocked_vfs.files = [
        mock_vfile_factory(path="/tmp/test.txt", content="", mode="rw"),
        mock_vfile_factory(
            path="/docs/readme.txt", content="read-only content", mode="ro"
        ),
        mock_vfile_factory(path="/docs/data.txt", content="initial content", mode="rw"),
        mock_vfile_factory(path="/docs/log.txt", content="line 1\n", mode="rw"),
        mock_vfile_factory(path="/docs/close_me.txt", content="", mode="rw"),
    ]

    def _resolve(path):
        for f in mocked_vfs.files:
            if f.path == path:
                return f
        raise FileNotFoundError(f"File {path} not found")

    mocked_vfs.resolve.side_effect = _resolve

    return mocked_vfs


@pytest.fixture
def mock_lock_manager_factory():
    """
    Factory fixture to create customized LockManager mocks.
    """

    def _create_lock_manager(acquire_result=(True, [], [])):
        mock_lm = MagicMock()
        mock_lm.locks = {}

        # Attach acquire_result to the mock object so it can be updated anytime
        mock_lm.acquire_result = acquire_result

        # Helper method for easy updating
        def set_acquire_result(result):
            mock_lm.acquire_result = result

        mock_lm.set_acquire_result = set_acquire_result

        def _acquire(agent, path, mode):
            # Read the CURRENT state of acquire_result from mock_lm
            granted, waiting_on, cycle = mock_lm.acquire_result

            mock_lock_holder = MagicMock()
            mock_lock_holder.holders = [agent] if granted else [waiting_on]
            if not granted and not cycle:
                mock_lock_holder.waiters = [agent]
            else:
                mock_lock_holder.waiters = []
            mock_lm.locks[path] = mock_lock_holder

            return mock_lm.acquire_result

        def _release(agent, path):
            if path in mock_lm.locks:
                del mock_lm.locks[path]
            return []  # Always return a list of unblocked agents

        mock_lm.acquire.side_effect = _acquire
        mock_lm.release.side_effect = _release

        return mock_lm

    return _create_lock_manager


@pytest.fixture
def mock_file_handle_factory():
    """Helper fixture to create mocked FileHandles."""

    def _create_file_handle(id, path, mode, agentId):
        file_handle = MagicMock(spec=FileHandle)
        file_handle.id = id
        file_handle.path = path
        file_handle.mode = mode
        file_handle.agentId = agentId
        return file_handle

    return _create_file_handle


class TestThinkOp:
    def test_think_op_initialization(self):
        op = ThinkOp(duration=5)
        assert op.duration == 5
        assert op.remaining == 5

    @pytest.mark.parametrize("invalid_duration", [0, -1, -100])
    def test_think_op_invalid_duration(self, invalid_duration):
        with pytest.raises(ValueError):
            ThinkOp(duration=invalid_duration)

    def test_think_op_execution_running(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        mock_agent = mock_agent_factory()

        op = ThinkOp(duration=5)

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "RUNNING"
        assert event_type == EventType.THINKING
        assert detail == "mock_agent THINKING"
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 4

    def test_think_op_execution_done(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        mock_agent = mock_agent_factory()

        op = ThinkOp(duration=1)

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.THINK_DONE
        assert detail == "mock_agent THINKING\n    mock_agent FINISHED THINKING"
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
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

    def test_open_op_successful_execute(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        """Standard Case: Lock acquired successfully. Creates handle and returns DONE."""
        mock_agent = mock_agent_factory()

        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.OPEN_GRANTED
        assert detail == "mock_agent OPEN /tmp/test.txt write as h100 -> zakljucano"
        assert related == []
        assert path == "/tmp/test.txt"

        assert mock_agent.isPreemptible is False
        assert op.remaining == 0
        assert "/tmp/test.txt" in mock_lock_manager.locks

        assert "h100" in mock_agent.handles
        created_handle = mock_agent.handles["h100"]
        assert created_handle.id == "h100"
        assert created_handle.path == "/tmp/test.txt"
        assert created_handle.mode == "write"
        assert created_handle.agentId == mock_agent.id

    def test_open_op_failed_execute_blocks(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        """Standard Case: Lock acquire returns False. Blocks agent, returns BLOCKED."""
        mock_agent = mock_agent_factory()
        mock_agent2 = mock_agent_factory("mock_agent_2")

        mock_lock_manager = mock_lock_manager_factory()
        mock_lock_manager.acquire(mock_agent2, "/tmp/test.txt", "write")

        mock_lock_manager.set_acquire_result((False, ["mock_agent_2"], []))
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "BLOCKED"
        assert event_type == EventType.OPEN_BLOCKED
        assert (
            detail
            == "mock_agent OPEN /tmp/test.txt write as h100 -> blokiran, ceka mock_agent_2"
        )
        assert related == ["mock_agent_2"]
        assert path == "/tmp/test.txt"

        assert mock_agent.isPreemptible is False
        assert "h100" not in mock_agent.handles
        assert op.remaining == 1
        assert mock_agent.state == AgentState.BLOCKED
        assert mock_agent in mock_lock_manager.locks["/tmp/test.txt"].waiters

    def test_open_op_failed_execute_rejects(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        """Standard Case: Lock acquire detects cycle, returns REJECTED."""
        mock_agent = mock_agent_factory()
        mock_agent2 = mock_agent_factory("mock_agent_2")

        mock_lock_manager = mock_lock_manager_factory(
            (False, ["agent_2"], ["mock_agent", "mock_agent_2"])
        )
        # Setup cycle
        mock_lock_manager.acquire(mock_agent, "/docs/readme.txt", "write")
        mock_lock_manager.acquire(mock_agent2, "/tmp/test.txt", "write")
        mock_lock_manager.acquire(
            mock_agent2, "/docs/readme.txt", "write"
        )  # agent2 waits on agent1

        # agent1 attempts to acquire what agent2 holds -> cycle
        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "REJECTED"
        assert event_type == EventType.OPEN_REJECTED
        assert "odbijeno, nastao bi ciklus" in detail
        assert mock_agent2.id in detail
        assert related != []
        assert path == "/tmp/test.txt"

        assert mock_agent.isPreemptible is False
        assert "h100" not in mock_agent.handles

        assert op.remaining == 1
        assert mock_agent.state == AgentState.RUNNING
        assert mock_agent not in mock_lock_manager.locks["/tmp/test.txt"].waiters

    def test_open_op_execution_error(
        self, mock_agent_factory, mock_lock_manager_factory
    ):
        """Edge Case: Ensure unexpected errors during execution are caught and returned as an ERROR tuple."""
        # Using an invalid VFS object intentionally to trigger an internal error inside execute()
        mock_agent = mock_agent_factory()

        op = OpenOp(path="/tmp/test.txt", mode="write", handle="h100")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, None, mock_lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.OPEN_ERROR
        assert (
            detail
            == "mock_agent OPEN /tmp/test.txt write as h100 -> GRESKA: desila se nepredvidjena greska"
        )
        assert path == "/tmp/test.txt"

        assert mock_agent.isPreemptible is False
        assert "h100" not in mock_agent.handles

        assert op.remaining == 1
        assert mock_agent.state == AgentState.RUNNING


class TestReadOp:
    def test_read_op_initialization(self):
        op = ReadOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_read_op_invalid_handle(self):
        with pytest.raises(ValueError):
            ReadOp(handle="")

    def test_read_op_execution_success(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()

        mock_agent.handles["h1"] = mock_file_handle_factory(
            id="h1", path="/docs/readme.txt", mode="ro", agentId=mock_agent.id
        )
        op = ReadOp(handle="h1")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.READ_DONE
        assert (
            detail
            == "mock_agent READ h1.\n--------đ---- Output ------------\n read-only content\n--------------------------------"
        )
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 0

    def test_read_op_execution_fails_missing_handle(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        mock_agent = mock_agent_factory()

        """Edge Case: Missing handle throws internally, caught and mapped to ERROR tuple."""
        op = ReadOp(handle="missing_h")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.READ_ERROR
        assert (
            detail
            == "mock_agent READ missing_h -> GRESKA: desila se nepredvidjena greska"
        )
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
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

    def test_write_op_execution_success(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()

        mock_agent.handles["h_write"] = mock_file_handle_factory(
            id="h_write", path="/docs/data.txt", mode="rw", agentId=mock_agent.id
        )
        op = WriteOp(handle="h_write", data="Completely overwritten data.")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.WRITE_DONE
        assert detail == "mock_agent WRITE h_write 'Completely overwritten data.'"
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 0
        assert (
            mock_vfs.resolve("/docs/data.txt").read() == "Completely overwritten data."
        )

    def test_write_op_fails_if_invalid_mode(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()

        mock_agent.handles["h_write"] = mock_file_handle_factory(
            id="h_write", path="/docs/readme.txt", mode="ro", agentId=mock_agent.id
        )
        op = WriteOp(handle="h_write", data="Should not write")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.WRITE_ERROR
        assert (
            detail
            == "mock_agent WRITE h_write 'Should not write' -> GRESKA: desila se nepredvidjena greska"
        )
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 1


class TestAppendOp:
    def test_append_op_initialization(self):
        op = AppendOp(handle="h2", data="\nNew Line")
        assert op.handle == "h2"
        assert op.data == "\nNew Line"
        assert op.remaining == 1

    def test_append_op_execution_success(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()
        mock_agent.handles["h_append"] = mock_file_handle_factory(
            id="h_append", path="/docs/log.txt", mode="rw", agentId=mock_agent.id
        )
        op = AppendOp(handle="h_append", data="line 2")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.APPEND_DONE
        assert detail == "mock_agent APPEND h_append 'line 2'"
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 0
        assert mock_vfs.resolve("/docs/log.txt").read() == "line 1\nline 2"

    def test_append_op_fails_if_invalid_mode(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()

        mock_agent.handles["h_append"] = mock_file_handle_factory(
            id="h_append", path="/docs/readme.txt", mode="ro", agentId=mock_agent.id
        )
        op = AppendOp(handle="h_append", data="line 2")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.APPEND_ERROR
        assert (
            detail
            == "mock_agent APPEND h_append 'line 2' -> GRESKA: desila se nepredvidjena greska"
        )
        assert related == []
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 1


class TestCloseOp:
    def test_close_op_initialization(self):
        op = CloseOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_close_op_invalid_handle_init(self):
        with pytest.raises((ValueError, KeyError)):
            CloseOp(handle="invalid_handle")

    def test_close_op_execution_success(
        self,
        mock_agent_factory,
        mock_vfs,
        mock_lock_manager_factory,
        mock_file_handle_factory,
    ):
        mock_agent = mock_agent_factory()

        mock_lock_manager = mock_lock_manager_factory()
        mock_lock_manager.acquire(mock_agent, "/docs/close_me.txt", "write")
        mock_agent.handles["h_close"] = mock_file_handle_factory(
            id="h_close", path="/docs/close_me.txt", mode="rw", agentId=mock_agent.id
        )
        op = CloseOp(handle="h_close")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "DONE"
        assert event_type == EventType.CLOSE_DONE
        assert detail == "CLOSE h_close"
        assert related == []  # Since no agents were woken in this test scenario
        assert path == "/docs/close_me.txt"

        assert mock_agent.isPreemptible is False
        assert op.remaining == 0
        assert "h_close" not in mock_agent.handles
        assert "/docs/close_me.txt" not in mock_lock_manager.locks

    def test_close_op_execution_fails_missing_handle(
        self, mock_agent_factory, mock_vfs, mock_lock_manager_factory
    ):
        mock_agent = mock_agent_factory()

        op = CloseOp(handle="missing_h")

        mock_lock_manager = mock_lock_manager_factory()
        status, event_type, detail, related, path = op.execute(
            mock_agent, mock_vfs, mock_lock_manager
        )

        assert status == "ERROR"
        assert event_type == EventType.CLOSE_ERROR
        assert detail == "CLOSE missing_h\n -> GRESKA: desila se nepredvidjena greska"
        # Path is unresolvable when the handle is missing
        assert path is None

        assert mock_agent.isPreemptible is False
        assert op.remaining == 1


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        with pytest.raises(TypeError):
            Operation(remaining=1)
