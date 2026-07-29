from unittest.mock import MagicMock

import pytest

from src.scheduler_Slot import Slot


@pytest.fixture
def mock_agent():
    """Provides a mocked Agent object for testing Slot assignment."""
    agent = MagicMock()
    # Mocking the class name to simulate a real Agent instance if strict type checking is used
    agent.__class__.__name__ = "Agent"
    agent.id = "A1"
    return agent


@pytest.fixture
def mock_another_agent():
    """Provides a second mocked Agent to test reassignment."""
    agent = MagicMock()
    agent.__class__.__name__ = "Agent"
    agent.id = "A2"
    return agent


class TestSlotInitialization:
    def test_initialization_with_id_only(self):
        """Standard Case: A slot initialized with only an ID should have no currentAgent."""
        slot = Slot(id=1)
        assert slot.id == 1
        assert slot.currentAgent is None

    def test_initialization_with_agent(self, mock_agent):
        """Standard Case: A slot initialized with an ID and an Agent."""
        slot = Slot(id=2, currentAgent=mock_agent)
        assert slot.id == 2
        assert slot.currentAgent is mock_agent

    @pytest.mark.parametrize("invalid_id", ["1", 1.5, None, [], {}])
    def test_initialization_invalid_id_type(self, invalid_id):
        """Edge Case: The 'id' attribute must strictly be an integer."""
        with pytest.raises((TypeError, ValueError)):
            Slot(id=invalid_id)

    def test_initialization_invalid_agent_type(self):
        """Edge Case: The 'currentAgent' attribute must strictly be an Agent or None."""
        with pytest.raises((TypeError, ValueError)):
            Slot(id=3, currentAgent="InvalidAgentString")


class TestSlotAgentManagement:
    def test_assign_agent_to_empty_slot(self, mock_agent):
        """Standard Case: Assigning an agent to an empty slot."""
        slot = Slot(id=10)
        assert slot.currentAgent is None

        slot.currentAgent = mock_agent
        assert slot.currentAgent is mock_agent

    def test_reassign_agent(self, mock_agent, mock_another_agent):
        """Standard Case: Overwriting an existing agent in a slot."""
        slot = Slot(id=11, currentAgent=mock_agent)
        assert slot.currentAgent is mock_agent

        slot.currentAgent = mock_another_agent
        assert slot.currentAgent is mock_another_agent

    def test_clear_agent(self, mock_agent):
        """Standard Case: Clearing a slot by setting currentAgent to None."""
        slot = Slot(id=12, currentAgent=mock_agent)
        assert slot.currentAgent is not None

        slot.currentAgent = None
        assert slot.currentAgent is None

    @pytest.mark.parametrize("invalid_agent", [123, "Agent", [], {}])
    def test_assign_invalid_agent_type_raises_error(self, invalid_agent):
        """Edge Case: Assigning an invalid data type to currentAgent should raise an error."""
        slot = Slot(id=13)
        with pytest.raises((TypeError, ValueError)):
            slot.currentAgent = invalid_agent

    def test_id_is_read_only(self):
        """Edge Case: Slot ID should ideally be immutable after initialization."""
        slot = Slot(id=14)
        with pytest.raises((AttributeError, Exception)):
            # Assuming id is a protected/read-only property
            slot.id = 15
