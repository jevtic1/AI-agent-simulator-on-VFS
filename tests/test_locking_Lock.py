import pytest
from locking_Lock import Lock


class TestLockInitialization:
    @pytest.mark.parametrize("valid_type", ["shared", "exclusive"])
    def test_valid_initialization(self, valid_type):
        """Standard Case: Lock initializes correctly with valid path and type."""
        lock = Lock(path="/root/docs/file.txt", type=valid_type)

        assert lock.path == "/root/docs/file.txt"
        assert lock.type == valid_type
        # Arrays should initialize empty by default
        assert isinstance(lock.holders, list)
        assert len(lock.holders) == 0
        assert isinstance(lock.waiters, list)
        assert len(lock.waiters) == 0

    @pytest.mark.parametrize(
        "invalid_type", ["SHARED", "Exclusive", "read", "write", "", None, 123]
    )
    def test_initialization_invalid_type_raises_error(self, invalid_type):
        """Edge Case: Lock type must strictly be 'shared' or 'exclusive'."""
        with pytest.raises(ValueError):
            Lock(path="/root/docs/file.txt", type=invalid_type)

    @pytest.mark.parametrize("invalid_path", ["", None, 123, []])
    def test_initialization_invalid_path_raises_error(self, invalid_path):
        """Edge Case: Lock path must be a valid, non-empty string."""
        with pytest.raises(ValueError):
            Lock(path=invalid_path, type="shared")


class TestLockPropertiesMutation:
    def test_holders_list_mutation(self):
        """Standard Case: The holders array can accept and store string IDs."""
        lock = Lock(path="/file.txt", type="shared")

        lock.holders.append("agent_1")
        lock.holders.append("agent_2")

        assert len(lock.holders) == 2
        assert "agent_1" in lock.holders
        assert "agent_2" in lock.holders

        lock.holders.remove("agent_1")
        assert lock.holders == ["agent_2"]

    def test_waiters_list_mutation(self):
        """Standard Case: The waiters array can accept and store string IDs."""
        lock = Lock(path="/file.txt", type="exclusive")

        lock.waiters.append("agent_3")
        assert len(lock.waiters) == 1
        assert lock.waiters == ["agent_3"]

    def test_type_modification_valid(self):
        """Standard Case: Modifying the type post-initialization to a valid state should succeed."""
        lock = Lock(path="/file.txt", type="shared")
        lock.type = "exclusive"

        assert lock.type == "exclusive"

    @pytest.mark.parametrize("invalid_type", ["unknown", "", None, 1])
    def test_type_modification_invalid_raises_error(self, invalid_type):
        """Edge Case: Setting the type post-initialization to an invalid state must raise an error."""
        lock = Lock(path="/file.txt", type="shared")

        with pytest.raises(ValueError):
            lock.type = invalid_type
