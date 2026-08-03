from unittest.mock import MagicMock

import pytest

from src.logger_Event import Event, EventType
from src.logger_EventLogger import EventLogger


@pytest.fixture
def logger():
    return EventLogger()


@pytest.fixture
def event_arrival():
    mock_event = MagicMock(spec=Event)
    mock_event.__class__ = Event
    mock_event.time = 3
    mock_event.type = EventType.AGENT_ARRIVED
    mock_event.agent_id = "agent_1"
    mock_event.detail = "Mock detail."
    mock_event.path = "/mnt/data/file.txt"
    return mock_event


@pytest.fixture
def event_done():
    mock_event = MagicMock(spec=Event)
    mock_event.__class__ = Event
    mock_event.time = 3
    mock_event.type = EventType.OPERATION_DONE
    mock_event.agent_id = "agent_1"
    mock_event.detail = "Mock detail."
    return mock_event


class TestEventLogger:
    def test_initializes_with_empty_events_list(self, logger):
        assert hasattr(logger, "events")
        assert isinstance(logger.events, list)
        assert len(logger.events) == 0

    def test_log_single_valid_event(self, logger, event_arrival):
        logger.log(event_arrival)

        assert len(logger.events) == 1
        assert logger.events[0] is event_arrival

    def test_log_multiple_events_maintains_order(
        self, logger, event_arrival, event_done
    ):
        logger.log(event_arrival)
        logger.log(event_done)

        assert len(logger.events) == 2
        assert logger.events[0] is event_arrival
        assert logger.events[1] is event_done

    @pytest.mark.parametrize(
        "invalid_event",
        [
            None,
            "This is a string, not an event",
            123,
            {"time": 0, "type": "AGENT_ARRIVED", "agent_id": "agent_1"},
            [
                MagicMock(
                    spec=Event,
                    __class__=Event,
                    time=0,
                    type=EventType.AGENT_ARRIVED,
                    agent_id="agent_1",
                    detail="",
                )
            ],
        ],
    )
    def test_log_rejects_invalid_types(self, logger, invalid_event):
        with pytest.raises((TypeError, ValueError)):
            logger.log(invalid_event)

    def test_print_report_empty_logger(self, logger, capsys):
        agents = []
        slots = []
        mock_vfs = MagicMock()

        logger.printReport(agents, slots, mock_vfs)
        captured = capsys.readouterr()

        assert captured.out != ""
        assert captured.err == ""
        mock_vfs.snapshot.assert_called_once()

    def test_print_report_with_events(self, logger, event_arrival, event_done, capsys):
        logger.log(event_arrival)
        logger.log(event_done)

        mock_agent = MagicMock()
        mock_slot = MagicMock()
        mock_vfs = MagicMock()

        logger.printReport([mock_agent], [mock_slot], mock_vfs)
        captured = capsys.readouterr()

        assert "agent_1" in captured.out
        assert "AGENT_ARRIVED" in captured.out
        assert "OPERATION_DONE" in captured.out
        assert "Mock detail." in captured.out
        assert "/mnt/data/file.txt" in captured.out
        assert captured.err == ""

        # Verify that summary is called for both agent and slot, and snapshot for vfs
        mock_agent.report_row.assert_called_once()
        mock_slot.gantt_row.assert_called_once()
        mock_vfs.snapshot.assert_called_once()

    def test_print_report_does_not_clear_events(self, logger, event_arrival):
        logger.log(event_arrival)

        mock_agent = MagicMock()
        mock_slot = MagicMock()
        mock_vfs = MagicMock()

        logger.printReport([mock_agent], [mock_slot], mock_vfs)

        assert len(logger.events) == 1
