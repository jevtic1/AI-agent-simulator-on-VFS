"""
Test suite for AgentState.

ASSUMED API CONTRACT (implementation does not exist yet — TDD):

    from src.models import AgentState

    class AgentState(Enum):
        NEW = ...
        READY = ...
        RUNNING = ...
        BLOCKED = ...
        TERMINATED = ...

        @classmethod
        def is_valid_transition(cls, frm: "AgentState", to: "AgentState") -> bool:
            '''Return True if transitioning from `frm` to `to` is legal.'''

Assumed transition rules (derived from the project design):
    NEW        -> READY                          (agent enters ready queue on arrival)
    READY      -> RUNNING                         (scheduler assigns a slot)
    RUNNING    -> READY                            (preemption, only at an op boundary)
    RUNNING    -> BLOCKED                          (OPEN would block on a lock)
    RUNNING    -> TERMINATED                       (agent finishes its last operation)
    BLOCKED    -> READY                            (lock released -> rejoins ready queue,
                                                      since blocked agents don't hold a slot)
    TERMINATED -> (nothing; terminal state)
    NEW        -> (nothing else; only ever moves to READY)
    self-transitions (X -> X) are NOT valid for any state
    any transition not listed above is NOT valid

If the actual implementation uses different method/member names, update the
IMPORT block and `is_valid_transition` invocations below — the test *cases*
and their intent should remain the source of truth.
"""

from enum import Enum

import pytest

# --- IMPORT BLOCK -----------------------------------------------------------
# Update this import path once the module is implemented.
from src.models_AgentState import AgentState

# --- Shared fixtures / constants --------------------------------------------

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

# every (frm, to) pair across the 5 states, minus the valid ones and self-pairs,
# generated programmatically so the invalid set can never silently drift from
# VALID_TRANSITIONS as states are added/removed
ALL_PAIRS = [(a, b) for a in ALL_STATES for b in ALL_STATES]
SELF_TRANSITIONS = [(a, a) for a in ALL_STATES]
INVALID_TRANSITIONS = [
    pair
    for pair in ALL_PAIRS
    if pair not in VALID_TRANSITIONS and pair not in SELF_TRANSITIONS
]


# =============================================================================
# 1. Membership / structural tests
# =============================================================================


class TestMembership:
    def test_agent_state_is_an_enum(self):
        assert issubclass(AgentState, Enum)

    def test_exactly_five_states_exist(self):
        assert len(list(AgentState)) == 5

    @pytest.mark.parametrize(
        "member_name", ["NEW", "READY", "RUNNING", "BLOCKED", "TERMINATED"]
    )
    def test_expected_member_exists(self, member_name):
        assert hasattr(AgentState, member_name)

    def test_no_unexpected_members(self):
        expected_names = {"NEW", "READY", "RUNNING", "BLOCKED", "TERMINATED"}
        actual_names = {member.name for member in AgentState}
        assert actual_names == expected_names

    def test_all_members_are_instances_of_agent_state(self):
        for state in AgentState:
            assert isinstance(state, AgentState)

    def test_member_values_are_unique(self):
        values = [member.value for member in AgentState]
        assert len(values) == len(set(values)), (
            "AgentState members must have unique values"
        )

    def test_members_are_hashable(self):
        # required since AgentState will likely be used as a dict key
        # (e.g. transition tables) or stored in a set
        state_set = {AgentState.NEW, AgentState.READY, AgentState.NEW}
        assert len(state_set) == 2

    def test_members_are_comparable_by_identity(self):
        assert AgentState.RUNNING == AgentState.RUNNING
        assert AgentState.RUNNING is AgentState.RUNNING

    def test_different_members_are_not_equal(self):
        assert AgentState.RUNNING != AgentState.BLOCKED

    def test_members_are_not_equal_to_plain_strings(self):
        # guards against accidental "state == 'RUNNING'" bugs elsewhere in the codebase
        assert AgentState.RUNNING != "RUNNING"
        assert AgentState.RUNNING != "running"

    def test_members_are_not_equal_to_none(self):
        for state in AgentState:
            assert state is not None
            assert state != None  # noqa: E711 (explicit check, not identity)


# =============================================================================
# 2. String / repr representation (matters for the event log output)
# =============================================================================


class TestStringRepresentation:
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
    def test_name_matches_expected_string(self, state, expected):
        assert state.name == expected

    def test_str_is_stable_and_non_empty_for_all_members(self):
        for state in AgentState:
            s = str(state)
            assert isinstance(s, str)
            assert len(s) > 0

    def test_repr_does_not_raise(self):
        for state in AgentState:
            assert repr(state) is not None


# =============================================================================
# 3. Valid transitions
# =============================================================================


class TestValidTransitions:
    @pytest.mark.parametrize("frm,to", VALID_TRANSITIONS)
    def test_valid_transition_returns_true(self, frm, to):
        assert AgentState.is_valid_transition(frm, to) is True

    def test_new_can_only_transition_to_ready(self):
        for target in ALL_STATES:
            expected = target is AgentState.READY
            assert AgentState.is_valid_transition(AgentState.NEW, target) is expected

    def test_running_has_three_valid_targets(self):
        valid_targets = {
            to for (frm, to) in VALID_TRANSITIONS if frm is AgentState.RUNNING
        }
        assert valid_targets == {
            AgentState.READY,
            AgentState.BLOCKED,
            AgentState.TERMINATED,
        }

    def test_blocked_can_only_transition_to_ready(self):
        for target in ALL_STATES:
            expected = target is AgentState.READY
            assert (
                AgentState.is_valid_transition(AgentState.BLOCKED, target) is expected
            )


# =============================================================================
# 4. Invalid transitions
# =============================================================================


class TestInvalidTransitions:
    @pytest.mark.parametrize("frm,to", INVALID_TRANSITIONS)
    def test_invalid_transition_returns_false(self, frm, to):
        assert AgentState.is_valid_transition(frm, to) is False

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_self_transition_is_always_invalid(self, state):
        assert AgentState.is_valid_transition(state, state) is False

    @pytest.mark.parametrize(
        "target",
        [
            AgentState.NEW,
            AgentState.READY,
            AgentState.RUNNING,
            AgentState.BLOCKED,
        ],
    )
    def test_terminated_is_a_true_terminal_state(self, target):
        # nothing should be reachable from TERMINATED, including back to NEW
        assert AgentState.is_valid_transition(AgentState.TERMINATED, target) is False

    def test_nothing_transitions_directly_into_new(self):
        # NEW should only ever be an agent's starting state, never a destination
        for state in ALL_STATES:
            if state is AgentState.NEW:
                continue
            assert AgentState.is_valid_transition(state, AgentState.NEW) is False

    def test_ready_cannot_skip_directly_to_blocked(self):
        # an agent must be RUNNING (attempting an OPEN) to become BLOCKED —
        # it can't block while merely waiting in the ready queue
        assert (
            AgentState.is_valid_transition(AgentState.READY, AgentState.BLOCKED)
            is False
        )

    def test_ready_cannot_skip_directly_to_terminated(self):
        # an agent must actually run its final operation to terminate
        assert (
            AgentState.is_valid_transition(AgentState.READY, AgentState.TERMINATED)
            is False
        )

    def test_blocked_cannot_transition_directly_to_running(self):
        # per design: a released agent re-enters the ready queue and must be
        # scheduled into a slot again, it doesn't resume running for free
        assert (
            AgentState.is_valid_transition(AgentState.BLOCKED, AgentState.RUNNING)
            is False
        )

    def test_blocked_cannot_transition_directly_to_terminated(self):
        assert (
            AgentState.is_valid_transition(AgentState.BLOCKED, AgentState.TERMINATED)
            is False
        )


# =============================================================================
# 5. Edge cases / defensive behavior
# =============================================================================


class TestEdgeCasesAndInputValidation:
    def test_is_valid_transition_rejects_none_as_from_state(self):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(None, AgentState.READY)

    def test_is_valid_transition_rejects_none_as_to_state(self):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(AgentState.READY, None)

    def test_is_valid_transition_rejects_string_instead_of_enum(self):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition("RUNNING", AgentState.READY)

    def test_is_valid_transition_rejects_integer_instead_of_enum(self):
        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(1, AgentState.READY)

    def test_is_valid_transition_rejects_foreign_enum_type(self):
        class UnrelatedEnum(Enum):
            FOO = "FOO"

        with pytest.raises((TypeError, ValueError)):
            AgentState.is_valid_transition(UnrelatedEnum.FOO, AgentState.READY)

    def test_constructing_agent_state_from_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AgentState("NOT_A_REAL_STATE")

    def test_agent_state_members_are_immutable(self):
        # enum members should not be reassignable
        with pytest.raises(AttributeError):
            AgentState.RUNNING = "something else"

    def test_transition_matrix_is_exhaustive_and_consistent(self):
        """
        Sanity check that every possible (frm, to) pair across all 5 states
        is classified as exactly one of: valid, self-transition (invalid),
        or invalid — with no pair silently unhandled or double-counted.
        """
        total_pairs = len(ALL_STATES) ** 2
        classified = (
            len(VALID_TRANSITIONS) + len(SELF_TRANSITIONS) + len(INVALID_TRANSITIONS)
        )
        assert classified == total_pairs

        for frm in ALL_STATES:
            for to in ALL_STATES:
                result = AgentState.is_valid_transition(frm, to)
                assert isinstance(result, bool), (
                    f"is_valid_transition({frm}, {to}) must return a bool, got {type(result)}"
                )
