from dataclasses import FrozenInstanceError
from enum import Enum

import pytest
from src.logger_Event import Event, EventType

# Standard test constants
TYPE = EventType.AGENT_ARRIVED
TIME = 100
AGENT_ID = "agent_42"
DETAIL = "Executed successfully."
RELATED_AGENTS = ["agent_99", "agent_100"]
PATH = "/mnt/data/file.txt"

VALIDATION_ERRORS = (ValueError, TypeError)


class TestEventTypeEnum:
    def test_enum_structure(self):
        assert issubclass(EventType, Enum)
        assert len(list(EventType)) == 21

    @pytest.mark.parametrize(
        "member_name",
        [
            "AGENT_ARRIVED",
            "SLOT_ASSIGNED",
            "SLOT_FREED",
            "PREEMPTED",
            "THINKING",
            "THINK_DONE",
            "OPEN_GRANTED",
            "OPEN_BLOCKED",
            "OPEN_REJECTED",
            "OPEN_ERROR",
            "READ_DONE",
            "READ_ERROR",
            "WRITE_DONE",
            "WRITE_ERROR",
            "APPEND_DONE",
            "APPEND_ERROR",
            "CLOSE_DONE",
            "CLOSE_ERROR",
            "UNKNOWN_ERROR",
            "OPERATION_DONE",
            "AGENT_TERMINATED",
        ],
    )
    def test_expected_members_exist(self, member_name):
        assert hasattr(EventType, member_name)

    def test_enum_members_are_unique(self):
        values = [m.value for m in EventType]
        assert len(values) == len(set(values))


class TestEventConstruction:
    def test_valid_instantiation_all_args(self):
        event = Event(
            time=TIME,
            type=TYPE,
            agent_id=AGENT_ID,
            detail=DETAIL,
            related_agent_ids=RELATED_AGENTS,
            path=PATH,
        )
        assert event.time == TIME
        assert event.type == TYPE
        assert event.agent_id == AGENT_ID
        assert event.detail == DETAIL
        assert event.related_agent_ids == RELATED_AGENTS
        assert event.path == PATH

    def test_valid_instantiation_defaults(self):
        event = Event(time=TIME, type=TYPE, agent_id=AGENT_ID, detail=DETAIL)
        # Allows for the default to be an empty list or None depending on the implementation
        assert not event.related_agent_ids
        assert event.path is None

    def test_positional_arguments(self):
        event = Event(TIME, TYPE, AGENT_ID, DETAIL, RELATED_AGENTS, PATH)
        assert (
            event.time,
            event.type,
            event.agent_id,
            event.detail,
            event.related_agent_ids,
            event.path,
        ) == (TIME, TYPE, AGENT_ID, DETAIL, RELATED_AGENTS, PATH)


class TestEventValidation:
    @pytest.mark.parametrize("invalid_time", [-1, "100", 10.5, None])
    def test_invalid_time_rejected(self, invalid_time):
        with pytest.raises(VALIDATION_ERRORS):
            Event(time=invalid_time, type=TYPE, agent_id=AGENT_ID, detail=DETAIL)

    @pytest.mark.parametrize("invalid_type", ["AGENT_ARRIVED", 1, None])
    def test_invalid_type_rejected(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            Event(time=TIME, type=invalid_type, agent_id=AGENT_ID, detail=DETAIL)

    @pytest.mark.parametrize("invalid_agent_id", ["", "   ", None, 123])
    def test_invalid_agent_id_rejected(self, invalid_agent_id):
        with pytest.raises(VALIDATION_ERRORS):
            Event(time=TIME, type=TYPE, agent_id=invalid_agent_id, detail=DETAIL)

    @pytest.mark.parametrize("invalid_detail", [None, 123, []])
    def test_invalid_detail_rejected(self, invalid_detail):
        with pytest.raises(VALIDATION_ERRORS):
            Event(time=TIME, type=TYPE, agent_id=AGENT_ID, detail=invalid_detail)

    @pytest.mark.parametrize(
        "invalid_related_agents",
        [
            "agent_99",  # Not a list
            [123],  # Invalid list element type
            ["", "   "],  # Invalid list element values (empty/whitespace)
        ],
    )
    def test_invalid_related_agents_rejected(self, invalid_related_agents):
        with pytest.raises(VALIDATION_ERRORS):
            Event(
                time=TIME,
                type=TYPE,
                agent_id=AGENT_ID,
                detail=DETAIL,
                related_agent_ids=invalid_related_agents,
            )

    @pytest.mark.parametrize("invalid_path", ["", "   ", 123, "relative/path.txt"])
    def test_invalid_path_rejected(self, invalid_path):
        with pytest.raises(VALIDATION_ERRORS):
            Event(
                time=TIME,
                type=TYPE,
                agent_id=AGENT_ID,
                detail=DETAIL,
                path=invalid_path,
            )


class TestEventImmutability:
    def test_fields_are_read_only(self):
        event = Event(time=TIME, type=TYPE, agent_id=AGENT_ID, detail=DETAIL)

        with pytest.raises((FrozenInstanceError, AttributeError)):
            event.time = 200

        with pytest.raises((FrozenInstanceError, AttributeError)):
            event.detail = "Changed"


class TestEventEdgeCases:
    def test_zero_time_is_accepted(self):
        event = Event(time=0, type=TYPE, agent_id=AGENT_ID, detail=DETAIL)
        assert event.time == 0

    def test_large_time_is_accepted(self):
        large_time = 999_999_999
        event = Event(time=large_time, type=TYPE, agent_id=AGENT_ID, detail=DETAIL)
        assert event.time == large_time

    def test_unicode_strings_accepted(self):
        event = Event(
            time=TIME,
            type=EventType.OPERATION_DONE,
            agent_id="agent_čćž",
            detail="Operacija završena.",
            path="/podaci/datoteka.txt",
        )
        assert event.agent_id == "agent_čćž"
        assert event.detail == "Operacija završena."
        assert event.type == EventType.OPERATION_DONE

    def test_empty_detail_string_is_accepted(self):
        event = Event(time=TIME, type=TYPE, agent_id=AGENT_ID, detail="")
        assert event.detail == ""
