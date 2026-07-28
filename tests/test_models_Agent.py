from enum import Enum

import pytest

from src.models_Agent import AgentState

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
