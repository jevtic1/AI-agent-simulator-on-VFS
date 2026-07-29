from unittest.mock import MagicMock

import pytest

from models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    Operation,
    ReadOp,
    ThinkOp,
    WriteOp,
)


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.id = "agent_1"
    agent.state = "RUNNING"
    agent.handles = {}
    agent.isPreemptive = True  # Setup default state to be True
    return agent


@pytest.fixture
def mock_vfile_rw():
    vfile = MagicMock()
    vfile.content = "initial content"
    vfile.mount = MagicMock()
    vfile.mount.mode = "rw"
    return vfile


@pytest.fixture
def mock_vfile_ro():
    vfile = MagicMock()
    vfile.content = "read-only content"
    vfile.mount = MagicMock()
    vfile.mount.mode = "ro"
    return vfile


@pytest.fixture
def mock_vfs(mock_vfile_rw):
    vfs = MagicMock()
    vfs.resolve.return_value = mock_vfile_rw
    return vfs


@pytest.fixture
def mock_lock_manager():
    lm = MagicMock()
    lm.acquire = MagicMock(return_value=True)
    lm.release = MagicMock(return_value=True)
    return lm


@pytest.fixture
def mock_file_handle():
    def _create_handle(path="/tmp/file.txt", mode="r"):
        handle = MagicMock()
        handle.path = path
        handle.mode = mode
        return handle

    return _create_handle


class TestThinkOp:
    def test_think_op_initialization(self):
        op = ThinkOp(duration=5)
        assert op.duration == 5
        assert op.remaining == 5

    @pytest.mark.parametrize("invalid_duration", [0, -1, -100])
    def test_think_op_invalid_duration(self, invalid_duration):
        with pytest.raises(ValueError):
            ThinkOp(duration=invalid_duration)

    def test_think_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        op = ThinkOp(duration=5)
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
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

    def test_open_op_successful_execute(self, mock_agent, mock_vfs, mock_lock_manager):
        op = OpenOp(path="/tmp/test.txt", mode="rw", handle="h100")
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining - 1

        # Verify handle was created and stored unconditionally
        assert "h100" in mock_agent.handles
        created_handle = mock_agent.handles["h100"]
        # Checking attributes assuming the handle is a simple object or FileHandle instance
        assert (
            getattr(created_handle, "path", None) == "/tmp/test.txt"
            or created_handle.path == "/tmp/test.txt"
        )
        assert (
            getattr(created_handle, "mode", None) == "rw" or created_handle.mode == "rw"
        )


class TestReadOp:
    def test_read_op_initialization(self):
        op = ReadOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_read_op_invalid_handle(self):
        with pytest.raises(ValueError):
            ReadOp(handle="")

    def test_read_op_execution_success(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle
    ):
        mock_agent.handles["h1"] = mock_file_handle(path="/docs/readme.txt", mode="r")
        op = ReadOp(handle="h1")
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining - 1
        mock_vfs.resolve.assert_called_once_with("/docs/readme.txt")

    def test_read_op_execution_fails_missing_handle(
        self, mock_agent, mock_vfs, mock_lock_manager
    ):
        op = ReadOp(handle="missing_h")
        initial_remaining = op.remaining

        with pytest.raises((KeyError, ValueError, AttributeError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
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

    def test_write_op_execution_success(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_rw
    ):
        mock_agent.handles["h_write"] = mock_file_handle(
            path="/docs/data.txt", mode="w"
        )
        mock_vfs.resolve.return_value = mock_vfile_rw

        op = WriteOp(handle="h_write", data="Completely overwritten data.")
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining - 1
        mock_vfs.resolve.assert_called_once_with("/docs/data.txt")
        # Must verify the file string was properly overwritten
        assert mock_vfile_rw.content == "Completely overwritten data."

    def test_write_op_fails_if_invalid_mode(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_rw
    ):
        mock_agent.handles["h_write"] = mock_file_handle(
            path="/docs/data.txt", mode="r"
        )
        mock_vfs.resolve.return_value = mock_vfile_rw

        op = WriteOp(handle="h_write", data="Should not write")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining  # Check no decrement on fail

    def test_write_op_fails_if_mount_readonly(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_ro
    ):
        mock_agent.handles["h_write"] = mock_file_handle(
            path="/docs/data.txt", mode="w"
        )
        mock_vfs.resolve.return_value = mock_vfile_ro

        op = WriteOp(handle="h_write", data="Should not write")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining


class TestAppendOp:
    def test_append_op_initialization(self):
        op = AppendOp(handle="h2", data="\nNew Line")
        assert op.handle == "h2"
        assert op.data == "\nNew Line"
        assert op.remaining == 1

    def test_append_op_execution_success(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_rw
    ):
        mock_agent.handles["h_append"] = mock_file_handle(
            path="/docs/log.txt", mode="a"
        )
        mock_vfile_rw.content = "line 1\n"
        mock_vfs.resolve.return_value = mock_vfile_rw

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining - 1
        mock_vfs.resolve.assert_called_once_with("/docs/log.txt")
        # Must verify the file string was properly appended
        assert mock_vfile_rw.content == "line 1\nline 2"

    def test_append_op_fails_if_invalid_mode(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_rw
    ):
        mock_agent.handles["h_append"] = mock_file_handle(
            path="/docs/log.txt", mode="r"
        )
        mock_vfs.resolve.return_value = mock_vfile_rw

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining

    def test_append_op_fails_if_mount_readonly(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle, mock_vfile_ro
    ):
        mock_agent.handles["h_append"] = mock_file_handle(
            path="/docs/log.txt", mode="a"
        )
        mock_vfs.resolve.return_value = mock_vfile_ro

        op = AppendOp(handle="h_append", data="line 2")
        initial_remaining = op.remaining

        with pytest.raises((PermissionError, ValueError, IOError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining


class TestCloseOp:
    def test_close_op_initialization(self):
        op = CloseOp(handle="h1")
        assert op.handle == "h1"
        assert op.remaining == 1

    def test_close_op_invalid_handle_init(self):
        with pytest.raises((ValueError, KeyError)):
            CloseOp(handle="invalid_handle")

    def test_close_op_execution_success(
        self, mock_agent, mock_vfs, mock_lock_manager, mock_file_handle
    ):
        mock_agent.handles["h_close"] = mock_file_handle(
            path="/docs/close_me.txt", mode="w"
        )
        op = CloseOp(handle="h_close")
        initial_remaining = op.remaining

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining - 1
        # Verify lock manager was called with agent and handle path
        mock_lock_manager.release.assert_called_once_with(
            mock_agent, "/docs/close_me.txt"
        )
        # Verify handle was removed from agent
        assert "h_close" not in mock_agent.handles

    def test_close_op_execution_fails_missing_handle(
        self, mock_agent, mock_vfs, mock_lock_manager
    ):
        op = CloseOp(handle="missing_h")
        initial_remaining = op.remaining

        with pytest.raises((KeyError, ValueError, AttributeError)):
            op.execute(mock_agent, mock_vfs, mock_lock_manager)

        assert mock_agent.isPreemptive is False
        assert op.remaining == initial_remaining


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        with pytest.raises(TypeError):
            Operation(remaining=1)
