import pytest
from locking_LockRequest import LockRequest


class TestLockRequestInitialization:
    def test_valid_initialization(self):
        """Standard Case: LockRequest initializes correctly with valid strings."""
        req = LockRequest(agentId="agent_007", mode="read")

        assert req.agentId == "agent_007"
        assert req.mode == "read"

    def test_missing_arguments_raises_error(self):
        """Edge Case: Initialization must fail if required arguments are missing."""
        with pytest.raises(TypeError):
            LockRequest(agentId="agent_1")  # Missing mode

        with pytest.raises(TypeError):
            LockRequest(mode="write")  # Missing agentId

        with pytest.raises(TypeError):
            LockRequest()  # Missing both


class TestLockRequestImmutability:
    def test_agentId_is_immutable(self):
        """Standard Case: agentId cannot be modified after instantiation."""
        req = LockRequest(agentId="agent_1", mode="read")

        # Depending on the exact implementation (e.g., @property, frozen dataclass),
        # modifying an attribute typically raises an AttributeError or FrozenInstanceError.
        with pytest.raises(Exception) as exc_info:
            req.agentId = "agent_2"

        assert isinstance(
            exc_info.value, (AttributeError, TypeError, NotImplementedError, Exception)
        )

    def test_mode_is_immutable(self):
        """Standard Case: mode cannot be modified after instantiation."""
        req = LockRequest(agentId="agent_1", mode="write")

        with pytest.raises(Exception) as exc_info:
            req.mode = "read"

        assert isinstance(
            exc_info.value, (AttributeError, TypeError, NotImplementedError, Exception)
        )

    def test_cannot_add_dynamic_attributes(self):
        """Edge Case: A strict immutable class should ideally prevent adding new attributes dynamically."""
        req = LockRequest(agentId="agent_1", mode="read")

        with pytest.raises(Exception):
            req.unauthorized_attribute = "hacked"
