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
    return agent


@pytest.fixture
def mock_vfs():
    vfs = MagicMock()
    vfs.resolve = MagicMock()
    vfs.mount = MagicMock()
    return vfs


@pytest.fixture
def mock_lock_manager():
    lm = MagicMock()
    lm.acquire = MagicMock(return_value=True)
    lm.release = MagicMock(return_value=True)
    return lm


class TestThinkOp:
    def test_think_op_initialization(self):
        op = ThinkOp(duration=5)
        assert op.duration == 5

    @pytest.mark.parametrize("duration", [1, 10, 100])
    def test_think_op_execution(
        self, mock_agent, mock_vfs, mock_lock_manager, duration
    ):
        op = ThinkOp(duration=duration)
        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        mock_vfs.resolve.assert_not_called()
        mock_lock_manager.acquire.assert_not_called()

    @pytest.mark.parametrize("invalid_duration", [0, -1, -100])
    def test_think_op_invalid_duration(self, invalid_duration):
        with pytest.raises(ValueError):
            ThinkOp(duration=invalid_duration)


class TestOpenOp:
    def test_open_op_initialization(self):
        op = OpenOp(path="/file.txt", mode="r", handle="h1")
        assert op.path == "/file.txt"
        assert op.mode == "r"
        assert op.handle == "h1"

    def test_open_op_successful_execute(self, mock_agent, mock_vfs, mock_lock_manager):
        op = OpenOp(path="/tmp/test.txt", mode="rw", handle="h100")
        mock_lock_manager.acquire.return_value = True

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        mock_lock_manager.acquire.assert_called_once_with(
            mock_agent, "/tmp/test.txt", "rw"
        )
        mock_vfs.resolve.assert_called_once_with("/tmp/test.txt")

    def test_open_op_lock_acquisition_failed(
        self, mock_agent, mock_vfs, mock_lock_manager
    ):
        op = OpenOp(path="/locked/file.txt", mode="w", handle="h1")
        mock_lock_manager.acquire.return_value = False

        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        mock_lock_manager.acquire.assert_called_once()
        mock_vfs.resolve.assert_not_called()

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


class TestReadOp:
    def test_read_op_initialization(self):
        op = ReadOp(handle="h1")
        assert op.handle == "h1"

    def test_read_op_execution_success(self, mock_agent, mock_vfs, mock_lock_manager):
        op = ReadOp(handle="h1")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)

    def test_read_op_invalid_handle(self, mock_agent, mock_vfs, mock_lock_manager):
        with pytest.raises(ValueError):
            ReadOp(handle="")


class TestWriteOp:
    def test_write_op_initialization(self):
        op = WriteOp(handle="h1", data="Hello World")
        assert op.handle == "h1"
        assert op.data == "Hello World"

    def test_write_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        op = WriteOp(handle="h1", data="sample text")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)

    def test_write_op_empty_data(self, mock_agent, mock_vfs, mock_lock_manager):
        op = WriteOp(handle="h1", data="")
        assert op.data == ""
        op.execute(mock_agent, mock_vfs, mock_lock_manager)


class TestAppendOp:
    def test_append_op_initialization(self):
        op = AppendOp(handle="h2", data="\nNew Line")
        assert op.handle == "h2"
        assert op.data == "\nNew Line"

    def test_append_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        op = AppendOp(handle="h2", data="appended payload")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)


class TestCloseOp:
    def test_close_op_initialization(self):
        op = CloseOp(handle="h1")
        assert op.handle == "h1"

    def test_close_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        op = CloseOp(handle="h1")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)
        mock_lock_manager.release.assert_called_once()

    def test_close_op_invalid_handle(self, mock_agent, mock_vfs, mock_lock_manager):
        with pytest.raises((ValueError, KeyError)):
            op = CloseOp(handle="invalid_handle")
            op.execute(mock_agent, mock_vfs, mock_lock_manager)


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        with pytest.raises(TypeError):
            Operation()


class TestOperationRemainingAttribute:
    def test_think_op_remaining_initialization(self):
        """Standard Case: ThinkOp should initialize remaining equal to its duration."""
        op = ThinkOp(duration=7)
        assert hasattr(op, "remaining"), "ThinkOp is missing 'remaining' attribute."
        assert op.remaining == op.duration

    def test_open_op_remaining_initialization(self):
        """Standard Case: OpenOp should initialize remaining to 1."""
        op = OpenOp(path="/file.txt", mode="r", handle="h1")
        assert hasattr(op, "remaining"), "OpenOp is missing 'remaining' attribute."
        assert op.remaining == 1

    def test_read_op_remaining_initialization(self):
        """Standard Case: ReadOp should initialize remaining to 1."""
        op = ReadOp(handle="h1")
        assert hasattr(op, "remaining"), "ReadOp is missing 'remaining' attribute."
        assert op.remaining == 1

    def test_write_op_remaining_initialization(self):
        """Standard Case: WriteOp should initialize remaining to 1."""
        op = WriteOp(handle="h1", data="Hello")
        assert hasattr(op, "remaining"), "WriteOp is missing 'remaining' attribute."
        assert op.remaining == 1

    def test_append_op_remaining_initialization(self):
        """Standard Case: AppendOp should initialize remaining to 1."""
        op = AppendOp(handle="h2", data="\nNew Line")
        assert hasattr(op, "remaining"), "AppendOp is missing 'remaining' attribute."
        assert op.remaining == 1

    def test_close_op_remaining_initialization(self):
        """Standard Case: CloseOp should initialize remaining to 1."""
        op = CloseOp(handle="h1")
        assert hasattr(op, "remaining"), "CloseOp is missing 'remaining' attribute."
        assert op.remaining == 1

    def test_remaining_attribute_modification(self):
        """Standard Case: The remaining attribute should be modifiable."""
        op = ThinkOp(duration=10)
        assert op.remaining == 10
        op.remaining -= 1
        assert op.remaining == 9

        op2 = ReadOp(handle="h1")
        assert op2.remaining == 1
        op2.remaining -= 1
        assert op2.remaining == 0
