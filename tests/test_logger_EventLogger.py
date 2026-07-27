import pytest
from src.logger_EventLogger import EventLogger

from src.logger_Event import Event, EventType


@pytest.fixture
def logger():
    return EventLogger()


@pytest.fixture
def event_arrival():
    return Event(
        time=0,
        type=EventType.AGENT_ARRIVED,
        agent_id="agent_1",
        detail="Agent arrived at system.",
    )


@pytest.fixture
def event_done():
    return Event(
        time=10,
        type=EventType.OPERATION_DONE,
        agent_id="agent_1",
        detail="ReadOp finished.",
        path="/mnt/data/file.txt",
    )


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
                Event(
                    time=0, type=EventType.AGENT_ARRIVED, agent_id="agent_1", detail=""
                )
            ],
        ],
    )
    def test_log_rejects_invalid_types(self, logger, invalid_event):
        with pytest.raises((TypeError, ValueError)):
            logger.log(invalid_event)

    def test_print_report_empty_logger(self, logger, capsys):
        logger.printReport()
        captured = capsys.readouterr()

        assert captured.out != ""
        assert captured.err == ""

    def test_print_report_with_events(self, logger, event_arrival, event_done, capsys):
        logger.log(event_arrival)
        logger.log(event_done)

        logger.printReport()
        captured = capsys.readouterr()

        assert "agent_1" in captured.out
        assert "AGENT_ARRIVED" in captured.out
        assert "OPERATION_DONE" in captured.out
        assert "ReadOp finished." in captured.out
        assert "/mnt/data/file.txt" in captured.out
        assert captured.err == ""

    def test_print_report_does_not_clear_events(self, logger, event_arrival):
        logger.log(event_arrival)
        logger.printReport()

        assert len(logger.events) == 1
