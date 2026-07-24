from unittest.mock import MagicMock

import pytest

# Import your actual operations classes here once implemented.
# For demonstration/testing setup, ensure your classes match these names:
# from operations import (
#     Operation, ThinkOp, OpenOp, ReadOp, WriteOp, AppendOp, CloseOp
# )
from models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    Operation,
    ReadOp,
    ThinkOp,
    WriteOp,
)

# ============================================================================
# FIXTURES & MOCKS
# ============================================================================


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.id = "agent_1"
    agent.state = "RUNNING"
    return agent


@pytest.fixture
def mock_vfs():
    vfs = MagicMock()
    # Setup mock methods based on diagram
    vfs.resolve = MagicMock()
    vfs.mount = MagicMock()
    return vfs


@pytest.fixture
def mock_lock_manager():
    lm = MagicMock()
    lm.acquire = MagicMock(return_value=True)
    lm.release = MagicMock(return_value=True)
    return lm


# ============================================================================
# 1. ThinkOp TESTS
# ============================================================================


class TestThinkOp:
    def test_think_op_initialization(self):
        """Standard Case: Valid duration set."""
        op = ThinkOp(duration=5)
        assert op.duration == 5

    @pytest.mark.parametrize("duration", [1, 10, 100])
    def test_think_op_execution(
        self, mock_agent, mock_vfs, mock_lock_manager, duration
    ):
        """Standard Case: Successful execution of CPU thinking time."""
        op = ThinkOp(duration=duration)
        # Execute operation
        result = op.execute(mock_agent, mock_vfs, mock_lock_manager)

        # Verify VFS and LockManager were not touched
        mock_vfs.resolve.assert_not_called()
        mock_lock_manager.acquire.assert_not_called()

    @pytest.mark.parametrize("invalid_duration", [0, -1, -100])
    def test_think_op_invalid_duration(self, invalid_duration):
        """Edge Case: Zero or negative duration should raise ValueError."""
        with pytest.raises(ValueError):
            ThinkOp(duration=invalid_duration)


# ============================================================================
# 2. OpenOp TESTS
# ============================================================================


class TestOpenOp:
    def test_open_op_initialization(self):
        """Standard Case: Correct attributes set upon creation."""
        op = OpenOp(path="/file.txt", mode="r", handle="h1")
        assert op.path == "/file.txt"
        assert op.mode == "r"
        assert op.handle == "h1"

    def test_open_op_successful_execute(self, mock_agent, mock_vfs, mock_lock_manager):
        """Standard Case: Successfully acquire lock and resolve file handle."""
        op = OpenOp(path="/tmp/test.txt", mode="rw", handle="h100")
        mock_lock_manager.acquire.return_value = True

        result = op.execute(mock_agent, mock_vfs, mock_lock_manager)

        mock_lock_manager.acquire.assert_called_once_with(
            mock_agent, "/tmp/test.txt", "rw"
        )
        mock_vfs.resolve.assert_called_once_with("/tmp/test.txt")

    def test_open_op_lock_acquisition_failed(
        self, mock_agent, mock_vfs, mock_lock_manager
    ):
        """Edge Case: Lock acquisition fails (blocked by LockManager)."""
        op = OpenOp(path="/locked/file.txt", mode="w", handle="h1")
        mock_lock_manager.acquire.return_value = False

        result = op.execute(mock_agent, mock_vfs, mock_lock_manager)

        mock_lock_manager.acquire.assert_called_once()
        # VFS file resolution shouldn't happen if lock acquisition failed
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
        """Edge Case: Missing or empty attributes should raise ValueError."""
        with pytest.raises((ValueError, TypeError)):
            OpenOp(path=path, mode=mode, handle=handle)


# ============================================================================
# 3. ReadOp TESTS
# ============================================================================


class TestReadOp:
    def test_read_op_initialization(self):
        """Standard Case: Proper setup of handle attribute."""
        op = ReadOp(handle="h1")
        assert op.handle == "h1"

    def test_read_op_execution_success(self, mock_agent, mock_vfs, mock_lock_manager):
        """Standard Case: Successfully execute read on handle."""
        op = ReadOp(handle="h1")

        # Assume agent or mock_vfs resolves handle to file content
        op.execute(mock_agent, mock_vfs, mock_lock_manager)
        # Verify read operations against agent's open handles / vfs

    def test_read_op_invalid_handle(self, mock_agent, mock_vfs, mock_lock_manager):
        """Edge Case: Attempt to read from an uninitialized or empty handle."""
        with pytest.raises(ValueError):
            ReadOp(handle="")


# ============================================================================
# 4. WriteOp TESTS
# ============================================================================


class TestWriteOp:
    def test_write_op_initialization(self):
        """Standard Case: Setting handle and data attributes."""
        op = WriteOp(handle="h1", data="Hello World")
        assert op.handle == "h1"
        assert op.data == "Hello World"

    def test_write_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        """Standard Case: Write string data to an open file handle."""
        op = WriteOp(handle="h1", data="sample text")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)

    def test_write_op_empty_data(self, mock_agent, mock_vfs, mock_lock_manager):
        """Edge Case: Writing empty string to file."""
        op = WriteOp(handle="h1", data="")
        assert op.data == ""
        # Writing empty payload should still execute cleanly without errors
        op.execute(mock_agent, mock_vfs, mock_lock_manager)


# ============================================================================
# 5. AppendOp TESTS
# ============================================================================


class TestAppendOp:
    def test_append_op_initialization(self):
        """Standard Case: Initialization with handle and data."""
        op = AppendOp(handle="h2", data="\nNew Line")
        assert op.handle == "h2"
        assert op.data == "\nNew Line"

    def test_append_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        """Standard Case: Appending text data."""
        op = AppendOp(handle="h2", data="appended payload")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)


# ============================================================================
# 6. CloseOp TESTS
# ============================================================================


class TestCloseOp:
    def test_close_op_initialization(self):
        """Standard Case: Valid handle supplied."""
        op = CloseOp(handle="h1")
        assert op.handle == "h1"

    def test_close_op_execution(self, mock_agent, mock_vfs, mock_lock_manager):
        """Standard Case: Close handle and release associated locks."""
        op = CloseOp(handle="h1")
        op.execute(mock_agent, mock_vfs, mock_lock_manager)

        # Lock manager release check
        mock_lock_manager.release.assert_called_once()

    def test_close_op_invalid_handle(self, mock_agent, mock_vfs, mock_lock_manager):
        """Edge Case: Attempt to close non-existent or null handle."""
        with pytest.raises((ValueError, KeyError)):
            op = CloseOp(handle="invalid_handle")
            # If validated during execution:
            op.execute(mock_agent, mock_vfs, mock_lock_manager)


# ============================================================================
# 7. ABSTRACT CLASS CONSTRAINTS
# ============================================================================


class TestOperationAbstract:
    def test_cannot_instantiate_abstract_operation(self):
        """Edge Case: Attempting to directly instantiate abstract Operation class."""
        with pytest.raises(TypeError):
            Operation()
