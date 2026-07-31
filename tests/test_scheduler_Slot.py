from unittest.mock import MagicMock

import pytest

from src.scheduler_Slot import Slot, SlotInterval


@pytest.fixture
def mock_agent():
    """Provides a mocked Agent object for testing Slot assignment."""
    agent = MagicMock()
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


class TestSlotInterval:
    def test_initialization(self):
        """Standard Case: Valid initialization of SlotInterval."""
        interval = SlotInterval(startTime=10, endTime=20, agentId="A1")
        assert interval.startTime == 10
        assert interval.endTime == 20
        assert interval.agentId == "A1"

    def test_initialization_empty_slot(self):
        """Standard Case: SlotInterval when nobody occupies the slot (agentId is None)."""
        interval = SlotInterval(startTime=5, endTime=None, agentId=None)
        assert interval.startTime == 5
        assert interval.endTime is None
        assert interval.agentId is None

    @pytest.mark.parametrize("valid_agent_id", ["A1", "agent_123", "", None])
    def test_agent_id_allowed_types(self, valid_agent_id):
        """Standard Case: agent_id must accept str or None."""
        interval = SlotInterval(startTime=0, endTime=10, agentId=valid_agent_id)
        assert interval.agentId == valid_agent_id

    @pytest.mark.parametrize("invalid_agent_id", [123, 12.3, [], {}, True, MagicMock()])
    def test_agent_id_invalid_types_raise_error(self, invalid_agent_id):
        """Edge Case: agent_id must raise an error if type is not str or None."""
        with pytest.raises((TypeError, ValueError)):
            SlotInterval(startTime=0, endTime=10, agentId=invalid_agent_id)

    @pytest.mark.parametrize("invalid_time", ["10", 10.5, None, [], True])
    def test_invalid_startTime_types(self, invalid_time):
        """Edge Case: startTime must strictly be an integer."""
        with pytest.raises((TypeError, ValueError)):
            SlotInterval(startTime=invalid_time, endTime=20, agentId="A1")

    @pytest.mark.parametrize("invalid_time", ["20", 20.5, [], {}, True])
    def test_invalid_endTime_types(self, invalid_time):
        """Edge Case: endTime must strictly be an integer or None."""
        with pytest.raises((TypeError, ValueError)):
            SlotInterval(startTime=0, endTime=invalid_time, agentId="A1")

    def test_endTime_before_startTime_raises_error(self):
        """Edge Case: endTime cannot be strictly less than startTime."""
        with pytest.raises(ValueError):
            SlotInterval(startTime=10, endTime=5, agentId="A1")

    def test_startTime_is_constant_immutable(self):
        """Constraint Case: startTime must be a constant/immutable once created."""
        interval = SlotInterval(startTime=10, endTime=20, agentId="A1")
        with pytest.raises((AttributeError, Exception)):
            interval.startTime = 15

    def test_agentId_is_constant_immutable(self):
        """Constraint Case: agentId must be a constant/immutable once created."""
        interval = SlotInterval(startTime=10, endTime=20, agentId="A1")
        with pytest.raises((AttributeError, Exception)):
            interval.agentId = "A2"


class TestSlotInitialization:
    def test_initialization_with_id_only(self):
        """Standard Case: A slot initialized with only an ID should have no currentAgent and empty history."""
        slot = Slot(id=1)
        assert slot.id == 1
        assert slot.currentAgent is None
        assert hasattr(slot, "history")
        assert isinstance(slot.history, list)
        assert len(slot.history) == 0

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
            slot.id = 15


class TestSlotHistoryManagement:
    def test_openNewInterval_creates_first_entry(self, mock_agent):
        """Standard Case: Opening a new interval adds the first SlotInterval to history."""
        slot = Slot(id=20)
        slot.openNewInterval(clock=0, agent_id=mock_agent.id)

        assert len(slot.history) == 1
        assert slot.history[0].startTime == 0
        assert slot.history[0].endTime is None
        assert slot.history[0].agentId == "A1"

    def test_openNewInterval_appends_to_end(self, mock_agent, mock_another_agent):
        """Standard Case: Subsequent new intervals are correctly appended to the end of history."""
        slot = Slot(id=21)
        slot.openNewInterval(clock=0, agent_id=mock_agent.id)
        slot.openNewInterval(clock=5, agent_id=mock_another_agent.id)

        assert len(slot.history) == 2
        assert slot.history[-1].startTime == 5
        assert slot.history[-1].agentId == "A2"

    def test_openNewInterval_unoccupied(self):
        """Standard Case: Agent ID is None when nobody occupies the slot."""
        slot = Slot(id=22)
        slot.openNewInterval(clock=10, agent_id=None)

        assert len(slot.history) == 1
        assert slot.history[-1].agentId is None

    @pytest.mark.parametrize("invalid_agent_id", [123, 45.6, [], {}, MagicMock()])
    def test_openNewInterval_invalid_agent_id_raises_error(self, invalid_agent_id):
        """Edge Case: openNewInterval must reject agent_id if not str or None."""
        slot = Slot(id=23)
        with pytest.raises((TypeError, ValueError)):
            slot.openNewInterval(clock=0, agent_id=invalid_agent_id)

    def test_closeCurrentInterval_updates_endTime(self, mock_agent):
        """Standard Case: Closing an interval successfully updates the endTime of the last interval."""
        slot = Slot(id=24)
        slot.openNewInterval(clock=5, agent_id=mock_agent.id)
        slot.closeCurrentInterval(clock=15)

        assert len(slot.history) == 1
        assert slot.history[-1].endTime == 15
        assert slot.history[-1].startTime == 5

    def test_closeCurrentInterval_empty_history(self):
        """Edge Case: Attempting to close an interval when history is empty should raise an error."""
        slot = Slot(id=25)
        with pytest.raises((IndexError, ValueError)):
            slot.closeCurrentInterval(clock=5)

    @pytest.mark.parametrize("invalid_clock", ["15", 15.5, None, [], {}])
    def test_closeCurrentInterval_invalid_clock_type(self, mock_agent, invalid_clock):
        """Edge Case: Attempting to close an interval with a non-integer clock value should raise an error."""
        slot = Slot(id=26)
        slot.openNewInterval(clock=5, agent_id=mock_agent.id)

        with pytest.raises((TypeError, ValueError)):
            slot.closeCurrentInterval(clock=invalid_clock)

    def test_closeCurrentInterval_invalid_clock_before_start(self, mock_agent):
        """Edge Case: Attempting to close an interval at a time prior to its startTime should raise an error."""
        slot = Slot(id=27)
        slot.openNewInterval(clock=10, agent_id=mock_agent.id)

        with pytest.raises(ValueError):
            slot.closeCurrentInterval(clock=5)

    def test_full_history_lifecycle(self, mock_agent, mock_another_agent):
        """Standard Case: End-to-end integration of opening and closing multiple intervals back-to-back."""
        slot = Slot(id=28)

        # Agent 1 takes slot from 0 to 10
        slot.openNewInterval(clock=0, agent_id=mock_agent.id)
        slot.closeCurrentInterval(clock=10)

        # Slot is empty from 10 to 15
        slot.openNewInterval(clock=10, agent_id=None)
        slot.closeCurrentInterval(clock=15)

        # Agent 2 takes slot from 15 to 30
        slot.openNewInterval(clock=15, agent_id=mock_another_agent.id)
        slot.closeCurrentInterval(clock=30)

        assert len(slot.history) == 3

        # Verify first segment
        assert slot.history[0].startTime == 0
        assert slot.history[0].endTime == 10
        assert slot.history[0].agentId == "A1"

        # Verify idle segment
        assert slot.history[1].startTime == 10
        assert slot.history[1].endTime == 15
        assert slot.history[1].agentId is None

        # Verify second segment
        assert slot.history[2].startTime == 15
        assert slot.history[2].endTime == 30
        assert slot.history[2].agentId == "A2"
