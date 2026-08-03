from enum import Enum
from unittest.mock import MagicMock

import pytest

from src.models_Agent import Agent, AgentState
from src.models_Operations import Operation
from src.vfs_FileHandle import FileHandle

ALL_STATES = [
    AgentState.NEW,
    AgentState.READY,
    AgentState.RUNNING,
    AgentState.BLOCKED,
    AgentState.TERMINATED,
]

VALID_TRANSITIONS = [
    (AgentState.NEW, AgentState.READY),
    (AgentState.READY, AgentState.RUNNING),
    (AgentState.RUNNING, AgentState.READY),
    (AgentState.RUNNING, AgentState.BLOCKED),
    (AgentState.RUNNING, AgentState.TERMINATED),
    (AgentState.BLOCKED, AgentState.READY),
]

ALL_PAIRS = [(a, b) for a in ALL_STATES for b in ALL_STATES]
SELF_TRANSITIONS = [(a, a) for a in ALL_STATES]
INVALID_TRANSITIONS = [
    pair
    for pair in ALL_PAIRS
    if pair not in VALID_TRANSITIONS and pair not in SELF_TRANSITIONS
]


@pytest.fixture(autouse=True)
def isolate_agent_tests():
    """
    Automatically runs for every test. Clears the static all_agents
    list before and after each test to prevent state leakage.
    """
    Agent.clear_agents()
    yield
    Agent.clear_agents()


class TestAgentStateEnum:
    def test_enum_structure_and_members(self):
        assert issubclass(AgentState, Enum)
        assert len(list(AgentState)) == 5

        expected_names = {"NEW", "READY", "RUNNING", "BLOCKED", "TERMINATED"}
        assert {m.name for m in AgentState} == expected_names

        values = [m.value for m in AgentState]
        assert len(values) == len(set(values))

    def test_member_types_and_hashability(self):
        for state in AgentState:
            assert isinstance(state, AgentState)
            assert state is not None
            assert state != "RUNNING"
            assert state != "running"

        state_set = {AgentState.NEW, AgentState.READY, AgentState.NEW}
        assert len(state_set) == 2

    @pytest.mark.parametrize(
        "state,expected",
        [
            (AgentState.NEW, "NEW"),
            (AgentState.READY, "READY"),
            (AgentState.RUNNING, "RUNNING"),
            (AgentState.BLOCKED, "BLOCKED"),
            (AgentState.TERMINATED, "TERMINATED"),
        ],
    )
    def test_string_representation(self, state, expected):
        assert state.name == expected
        assert len(str(state)) > 0
        assert repr(state) is not None


class TestAgentStateTransitions:
    @pytest.mark.parametrize("frm,to", VALID_TRANSITIONS)
    def test_valid_transitions(self, frm, to):
        assert AgentState.is_valid_transition(frm, to) is True

    @pytest.mark.parametrize("frm,to", INVALID_TRANSITIONS)
    def test_invalid_transitions(self, frm, to):
        assert AgentState.is_valid_transition(frm, to) is False

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_self_transitions_invalid(self, state):
        assert AgentState.is_valid_transition(state, state) is False

    def test_specific_transition_rules(self):
        # NEW can only transition to READY
        for target in ALL_STATES:
            expected = target is AgentState.READY
            assert AgentState.is_valid_transition(AgentState.NEW, target) is expected

        # RUNNING targets
        running_targets = {
            to for (frm, to) in VALID_TRANSITIONS if frm is AgentState.RUNNING
        }
        assert running_targets == {
            AgentState.READY,
            AgentState.BLOCKED,
            AgentState.TERMINATED,
        }

        # BLOCKED can only transition to READY
        for target in ALL_STATES:
            expected = target is AgentState.READY
            assert (
                AgentState.is_valid_transition(AgentState.BLOCKED, target) is expected
            )

    @pytest.mark.parametrize(
        "target",
        [AgentState.NEW, AgentState.READY, AgentState.RUNNING, AgentState.BLOCKED],
    )
    def test_terminated_is_terminal(self, target):
        assert AgentState.is_valid_transition(AgentState.TERMINATED, target) is False

    def test_invalid_transition_shortcuts(self):
        # Nothing transitions back into NEW
        for state in ALL_STATES:
            if state is not AgentState.NEW:
                assert AgentState.is_valid_transition(state, AgentState.NEW) is False

        assert (
            AgentState.is_valid_transition(AgentState.READY, AgentState.BLOCKED)
            is False
        )
        assert (
            AgentState.is_valid_transition(AgentState.READY, AgentState.TERMINATED)
            is False
        )
        assert (
            AgentState.is_valid_transition(AgentState.BLOCKED, AgentState.RUNNING)
            is False
        )
        assert (
            AgentState.is_valid_transition(AgentState.BLOCKED, AgentState.TERMINATED)
            is False
        )


class TestAgentStateValidation:
    @pytest.mark.parametrize("invalid_arg", [None, "RUNNING", 1])
    def test_is_valid_transition_invalid_from_state(self, invalid_arg):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(invalid_arg, AgentState.READY)

    @pytest.mark.parametrize("invalid_arg", [None, "READY", 1])
    def test_is_valid_transition_invalid_to_state(self, invalid_arg):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(AgentState.READY, invalid_arg)

    def test_unrelated_enum_rejected(self):
        class UnrelatedEnum(Enum):
            FOO = "FOO"

        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(UnrelatedEnum.FOO, AgentState.READY)

    def test_construction_and_immutability(self):
        with pytest.raises(ValueError):
            AgentState("NOT_A_REAL_STATE")

        with pytest.raises(AttributeError):
            AgentState.RUNNING = "something else"

    def test_transition_matrix_coverage(self):
        total_pairs = len(ALL_STATES) ** 2
        classified = (
            len(VALID_TRANSITIONS) + len(SELF_TRANSITIONS) + len(INVALID_TRANSITIONS)
        )
        assert classified == total_pairs

        for frm in ALL_STATES:
            for to in ALL_STATES:
                res = AgentState.is_valid_transition(frm, to)
                assert isinstance(res, bool)


@pytest.fixture
def mock_operations():
    op1 = MagicMock(spec=Operation)
    op1.remaining = 0
    op2 = MagicMock(spec=Operation)
    op2.remaining = 0
    return [op1, op2]


@pytest.fixture
def agent(mock_operations):
    return Agent(id="A1", priority=1, arrival_time=0, operations=mock_operations)


class TestAgentStaticList:
    def test_agent_registration(self, mock_operations):
        """Test that instances are automatically registered in the static all_agents list."""
        assert len(Agent.all_agents) == 0

        agent1 = Agent(id="A1", priority=1, arrival_time=0, operations=mock_operations)
        assert len(Agent.all_agents) == 1
        assert Agent.all_agents[0] is agent1

        agent2 = Agent(id="A2", priority=2, arrival_time=0, operations=mock_operations)
        assert len(Agent.all_agents) == 2
        assert Agent.all_agents[1] is agent2

    def test_clear_agents(self, mock_operations):
        """Test that the utility method clears the list correctly."""
        Agent(id="A1", priority=1, arrival_time=0, operations=mock_operations)
        assert len(Agent.all_agents) == 1

        Agent.clear_agents()
        assert len(Agent.all_agents) == 0


class TestAgentInitialization:
    def test_initialization_defaults(self, agent, mock_operations):
        assert agent.id == "A1"
        assert agent.priority == 1
        assert agent.arrival_time == 0
        assert agent.operations == mock_operations

        assert agent.current_op_index == 0
        assert agent.state == AgentState.NEW
        assert agent.start_time == 0
        assert agent.end_time == 0
        assert agent.wait_time == 0
        assert agent.blocked_time == 0
        assert agent.preemption_count == 0
        assert isinstance(agent.handles, dict)
        assert len(agent.handles) == 0

    def test_initialization_invalid_priority(self, mock_operations):
        with pytest.raises(ValueError):
            Agent(id="A2", priority=-1, arrival_time=0, operations=mock_operations)

    def test_initialization_invalid_arrival_time(self, mock_operations):
        with pytest.raises(ValueError):
            Agent(id="A3", priority=1, arrival_time=-5, operations=mock_operations)


class TestAgentNextOperation:
    def test_next_operation_returns_current(self, agent, mock_operations):
        op = agent.nextOperation()
        assert op is mock_operations[0]

    def test_next_operation_out_of_bounds_returns_none(self, agent):
        agent.current_op_index = len(agent.operations)
        op = agent.nextOperation()
        assert op is None


class TestAgentAdvance:
    def test_advance_calls_execute_and_increments_if_zero_remaining(
        self, agent, mock_operations
    ):
        op = mock_operations[0]
        # Set to > 0 initially to prove the check happens AFTER execute()
        op.remaining = 1
        agent.isPreemptible = False

        vfs_mock = MagicMock()
        lock_manager_mock = MagicMock()

        expected_return = ("SUCCESS", None, "Operation completed", [], "/dummy/path")

        # Simulate execute() mutating the operation's remaining time
        def mock_execute(*args, **kwargs):
            op.remaining -= 1
            return expected_return

        op.execute.side_effect = mock_execute

        result = agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        # Assert execute was triggered during advance
        op.execute.assert_called_once_with(agent, vfs_mock, lock_manager_mock)

        # Verify index progresses and isPreemptible flag is reset because remaining is now 0
        assert agent.current_op_index == 1
        assert agent.isPreemptible is True
        assert result == expected_return

    def test_advance_calls_execute_does_not_increment_if_remaining_time(
        self, agent, mock_operations
    ):
        op = mock_operations[0]
        # Set to 2 initially, execute will drop it to 1
        op.remaining = 2
        agent.isPreemptible = False

        vfs_mock = MagicMock()
        lock_manager_mock = MagicMock()

        expected_return = ("PENDING", None, "Operation in progress", ["A2"], None)

        # Simulate execute() dropping remaining time, but not to 0
        def mock_execute(*args, **kwargs):
            op.remaining -= 1
            return expected_return

        op.execute.side_effect = mock_execute

        result = agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        op.execute.assert_called_once_with(agent, vfs_mock, lock_manager_mock)

        # Verify index and flag remain unaffected because remaining is not 0
        assert agent.current_op_index == 0
        assert agent.isPreemptible is False
        assert result == expected_return

    def test_advance_terminates_on_error(self, agent, mock_operations):
        """Test that advance sets agent state to TERMINATED if execute returns 'ERROR'."""
        op = mock_operations[0]
        op.remaining = 1

        vfs_mock = MagicMock()
        lock_manager_mock = MagicMock()

        # The first element of the return value is "ERROR"
        expected_return = ("ERROR", None, "GRESKA\n", [], None)

        def mock_execute(*args, **kwargs):
            return expected_return

        op.execute.side_effect = mock_execute

        result = agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        # Verify the state was set to TERMINATED immediately upon receiving "ERROR"
        assert agent.state == AgentState.TERMINATED
        assert result == expected_return

    def test_advance_updates_state_when_finished(self, agent, mock_operations):
        """Test that advance sets state to TERMINATED when current_op_index reaches len(operations)."""
        vfs_mock = MagicMock()
        lock_manager_mock = MagicMock()

        # Simulate both operations completing their work upon execution
        def execute_op0(*args, **kwargs):
            mock_operations[0].remaining = 0
            return ("DONE", None, "", [], None)

        def execute_op1(*args, **kwargs):
            mock_operations[1].remaining = 0
            return ("DONE", None, "", [], None)

        mock_operations[0].remaining = 1
        mock_operations[0].execute.side_effect = execute_op0

        mock_operations[1].remaining = 1
        mock_operations[1].execute.side_effect = execute_op1

        # First operation completes
        agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)
        assert agent.current_op_index == 1
        assert agent.state != AgentState.TERMINATED

        # Second (and final) operation completes
        agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        # Verify state is set to TERMINATED exactly when index equals length of operations list
        assert agent.current_op_index == len(agent.operations)
        assert agent.state == AgentState.TERMINATED

    def test_advance_does_not_execute_or_increment_past_end(
        self, agent, mock_operations
    ):
        vfs_mock = MagicMock()
        lock_manager_mock = MagicMock()

        def execute_op0(*args, **kwargs):
            mock_operations[0].remaining = 0
            return ("DONE", None, "", [], None)

        def execute_op1(*args, **kwargs):
            mock_operations[1].remaining = 0
            return ("DONE", None, "", [], None)

        mock_operations[0].remaining = 1
        mock_operations[0].execute.side_effect = execute_op0

        mock_operations[1].remaining = 1
        mock_operations[1].execute.side_effect = execute_op1

        # Advance through all operations
        agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)
        agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        # Final call out of bounds
        result = agent.advance(vfs=vfs_mock, lock_manager=lock_manager_mock)

        assert agent.current_op_index == len(agent.operations)
        assert agent.state == AgentState.TERMINATED

        # Ensure it didn't crash and operations were only executed the intended amount of times
        mock_operations[0].execute.assert_called_once()
        mock_operations[1].execute.assert_called_once()
        assert result[0] == "ERROR"
        assert result[1] == None
        assert result[2] == "GRESKA. Agent pozvan nakon svog kraja."


class TestAgentHandles:
    def test_add_handle(self, agent):
        mock_handle = MagicMock(spec=FileHandle)
        agent.handles["h1"] = mock_handle
        assert "h1" in agent.handles
        assert agent.handles["h1"] is mock_handle

    def test_remove_handle(self, agent):
        mock_handle = MagicMock(spec=FileHandle)
        agent.handles["h1"] = mock_handle
        del agent.handles["h1"]
        assert "h1" not in agent.handles


class TestAgentStateAndStats:
    def test_state_transitions(self, agent):
        agent.state = AgentState.READY
        assert agent.state == AgentState.READY

        agent.state = AgentState.RUNNING
        assert agent.state == AgentState.RUNNING

    def test_statistics_increments(self, agent):
        agent.wait_time += 1
        agent.blocked_time += 2
        agent.preemption_count += 1

        assert agent.wait_time == 1
        assert agent.blocked_time == 2
        assert agent.preemption_count == 1


class TestAgentPreemptibleAttribute:
    def test_initialization_default_preemptible(self, mock_operations):
        agent = Agent(
            id="A_default", priority=1, arrival_time=0, operations=mock_operations
        )
        assert agent.isPreemptible is True

    def test_initialization_explicit_preemptible_true(self, mock_operations):
        agent = Agent(
            id="A_true",
            priority=1,
            arrival_time=0,
            operations=mock_operations,
            isPreemptible=True,
        )
        assert agent.isPreemptible is True

    def test_initialization_explicit_preemptible_false(self, mock_operations):
        agent = Agent(
            id="A_false",
            priority=1,
            arrival_time=0,
            operations=mock_operations,
            isPreemptible=False,
        )
        assert agent.isPreemptible is False

    def test_preemptible_attribute_modification(self, mock_operations):
        agent = Agent(
            id="A_modify", priority=1, arrival_time=0, operations=mock_operations
        )
        assert agent.isPreemptible is True
        agent.isPreemptible = False
        assert agent.isPreemptible is False


class TestAgentReportRow:
    def test_report_row_formatting(self, agent):
        """Verifies report_row() correctly maps attributes and formats strings."""
        agent.state = AgentState.TERMINATED
        agent.arrival_time = 0
        agent.start_time = 0
        agent.end_time = 6
        agent.wait_time = 0
        agent.blocked_time = 2
        agent.preemption_count = 0

        row = agent.report_row()

        assert isinstance(row, str)
        assert "A1" in row
        assert "zavrsen" in row
        assert "6" in row
        assert "2" in row


class TestAgentClassStats:
    def test_calculate_average_stats_with_agents(self, mock_operations):
        """Tests that the static method correctly calculates and formats average wait and block times."""
        a1 = Agent(id="A1", priority=1, arrival_time=0, operations=mock_operations)
        a1.wait_time = 0
        a1.blocked_time = 2

        a2 = Agent(id="A2", priority=1, arrival_time=0, operations=mock_operations)
        a2.wait_time = 0
        a2.blocked_time = 0

        # Expect wait_time average 0.00, blocked_time average 1.00
        result = Agent.calculate_average_stats()

        assert (
            result
            == "Prosjecno vrijeme čekanja: 0.00\nProsjecno vrijeme blokiranja: 1.00"
        )

    def test_calculate_average_stats_empty(self):
        """Tests calculating averages when no agents exist in the static list."""
        # Note: The test environment automatically clears the list via the isolate_agent_tests fixture
        result = Agent.calculate_average_stats()

        assert (
            result
            == "Prosjecno vrijeme čekanja: 0.00\nProsjecno vrijeme blokiranja: 0.00"
        )
