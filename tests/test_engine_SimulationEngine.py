import sys
from unittest.mock import ANY, MagicMock, patch

import pytest

# Dependencies based on provided system specifications
from engine_SimulationEngine import SimulationEngine
from logger_Event import Event, EventType
from models_Agent import Agent, AgentState


@pytest.fixture
def mock_event_factory():
    """Helper fixture to create mocked Events without triggering dataclass validation."""

    def _create_event(
        time: int,
        event_type: EventType,
        agent_id: str,
        detail: str = "Mock detail",
        related_agent_ids: list[str] | None = None,
        path: str | None = None,
    ):
        event = MagicMock(spec=Event)
        event.time = time
        event.type = event_type
        event.agent_id = agent_id
        event.detail = detail
        event.related_agent_ids = related_agent_ids
        event.path = path
        return event

    return _create_event


@pytest.fixture
def mock_scheduler():
    """Provides a mocked Scheduler to control readyQueue and slot assignments."""
    scheduler = MagicMock()
    scheduler.slots = []
    scheduler.enqueue_ready_agent = MagicMock()
    scheduler.scheduleNext = MagicMock(return_value=[])
    return scheduler


@pytest.fixture
def mock_logger():
    """Provides a mocked EventLogger."""
    return MagicMock()


@pytest.fixture
def mock_agent():
    """Helper fixture to create mocked Agents."""

    def _create_agent(agent_id, arrival_time, state=AgentState.NEW):
        agent = MagicMock(spec=Agent)
        agent.id = agent_id
        agent.priority = 2
        agent.arrival_time = arrival_time
        agent.state = state
        agent.advance = MagicMock(return_value="MOCK_OUTCOME")
        return agent

    return _create_agent


@pytest.fixture
def mock_slot_factory():
    """Helper fixture to create mocked Slots."""

    def _create_slot(slot_id, current_agent=None):
        slot = MagicMock()
        slot.id = slot_id
        slot.currentAgent = current_agent
        slot.closeCurrentInterval = MagicMock()
        slot.openNewInterval = MagicMock()
        return slot

    return _create_slot


@pytest.fixture
def engine(mock_scheduler, mock_logger):
    """Initializes the SimulationEngine with mocked dependencies."""
    return SimulationEngine(
        agents=[],
        scheduler=mock_scheduler,
        logger=mock_logger,
        vfs=MagicMock(),
        lock_manager=MagicMock(),
    )


class TestSimulationEngineTick:
    """Tests the Phase 1, Phase 2, Phase 3, and return rules of the tick() method."""

    def test_tick_phase1_arrivals_enqueues_correct_agents(
        self,
        engine,
        mock_scheduler,
        mock_logger,
        mock_agent,
        mock_event_factory,
    ):
        """Standard Case: Agents arriving at the current clock get enqueued and logged."""
        engine.clock = 5
        agent1 = mock_agent("agent_1", arrival_time=5, state=AgentState.NEW)
        agent2 = mock_agent("agent_2", arrival_time=10, state=AgentState.NEW)
        engine.agents = [agent1, agent2]

        engine.tick()

        # Check Phase 1 operations for the arrived agent
        assert agent1.state == AgentState.READY
        mock_scheduler.enqueue_ready_agent.assert_called_once_with(agent1)

        # Verify the arrival event was logged
        actual_event = mock_logger.log.call_args[0][0]
        assert actual_event.time == 5
        assert actual_event.type == EventType.AGENT_ARRIVED
        assert actual_event.agent_id == "agent_1"

        # The future agent should be ignored this tick
        assert agent2.state == AgentState.NEW

    def test_tick_phase2_scheduling_assigns_slots_and_logs(
        self,
        engine,
        mock_scheduler,
        mock_logger,
        mock_agent,
        mock_slot_factory,
        mock_event_factory,
    ):
        """Standard Case: newlyAssigned agents have their intervals updated on the slot."""
        engine.clock = 5

        # Setup newly assigned pair
        mock_agent_instance = mock_agent("agent_X", arrival_time=0)
        mock_slot = mock_slot_factory(slot_id=0, current_agent=mock_agent_instance)

        # scheduleNext returns the newly assigned tuple based on prompt design constraints
        mock_scheduler.scheduleNext.return_value = [(mock_slot, mock_agent_instance)]

        engine.tick()

        # Slot metrics should be finalized for prior state and opened for new agent
        mock_slot.closeCurrentInterval.assert_called_once_with(engine.clock - 1)
        mock_slot.openNewInterval.assert_called_once_with(engine.clock - 1, "agent_X")

        # Must log the slot assignment
        actual_event = mock_logger.log.call_args[0][0]
        assert actual_event.time == 5
        assert actual_event.type == EventType.SLOT_ASSIGNED
        assert actual_event.agent_id == "agent_X"

    def test_tick_phase3_execution_advances_only_existing_running_agents(
        self, engine, mock_scheduler, mock_agent, mock_slot_factory
    ):
        """Standard Case: Slots occupied BEFORE phase 2 advance. newlyAssigned slots wait until next tick."""
        engine.clock = 10
        engine.handle = MagicMock()  # Mock internal handler

        existing_agent = mock_agent("agent_EXISTING", arrival_time=0)
        new_agent = mock_agent("agent_NEW", arrival_time=5)

        existing_slot = mock_slot_factory(slot_id=0, current_agent=existing_agent)
        new_slot = mock_slot_factory(slot_id=1, current_agent=new_agent)
        empty_slot = mock_slot_factory(slot_id=2, current_agent=None)

        mock_scheduler.slots = [existing_slot, new_slot, empty_slot]
        mock_scheduler.scheduleNext.return_value = [(new_slot, new_agent)]

        engine.tick()

        # Phase 3 validations
        existing_agent.advance.assert_called_once()
        engine.handle.assert_called_once_with(
            existing_agent, "MOCK_OUTCOME", existing_slot, engine.clock - 1
        )

        # Edge Case: Newly assigned slot must NOT advance in the same tick it was scheduled
        new_agent.advance.assert_not_called()

    def test_tick_returns_false_if_all_agents_terminated(self, engine, mock_agent):
        """Return Condition: tick() returns False immediately if all agents are TERMINATED."""
        agent1 = mock_agent("A", 0, state=AgentState.TERMINATED)
        agent2 = mock_agent("B", 0, state=AgentState.TERMINATED)
        engine.agents = [agent1, agent2]

        result = engine.tick()

        assert result is False

    def test_tick_returns_true_if_agents_still_active(self, engine, mock_agent):
        """Return Condition: tick() returns True if ANY agent is not TERMINATED."""
        agent1 = mock_agent("A", 0, state=AgentState.TERMINATED)
        agent2 = mock_agent("B", 0, state=AgentState.RUNNING)
        engine.agents = [agent1, agent2]

        result = engine.tick()

        assert result is True


class TestSimulationEngineHandle:
    """Tests the handle() method of SimulationEngine."""

    def test_handle_logs_event_and_keeps_slot_on_success(
        self, engine, mock_slot_factory
    ):
        """Standard Case: A successful/pending agent execution logs an event but remains in the slot."""
        mock_slot = mock_slot_factory(slot_id=1, current_agent="agent_1")
        # outcome tuple structure: (status, event_type, detail, related_agent_ids, path)
        outcome = (
            "SUCCESS",
            EventType.READ_DONE,
            "File read successfully",
            [],
            None,
        )

        engine.handle("agent_1", outcome, mock_slot, 15)

        # Verify the event was correctly parsed and logged
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 15
        assert actual_event.type == EventType.READ_DONE
        assert actual_event.agent_id == "agent_1"
        assert actual_event.detail == "File read successfully"
        assert actual_event.related_agent_ids == []
        assert actual_event.path is None

        # Verify the slot was NOT released
        assert mock_slot.currentAgent == "agent_1"

    def test_handle_logs_event_and_releases_slot_on_terminated(
        self, engine, mock_slot_factory
    ):
        """Standard Case: If an agent's outcome status is TERMINATED, the slot must be released."""
        mock_slot = mock_slot_factory(slot_id=1, current_agent="agent_1")
        outcome = (
            "TERMINATED",
            EventType.AGENT_TERMINATED,
            "Agent completed operations",
            [],
            None,
        )

        engine.handle("agent_1", outcome, mock_slot, 20)

        # Verify the completion event was logged
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 20
        assert actual_event.type == EventType.AGENT_TERMINATED
        assert actual_event.agent_id == "agent_1"

        # Verify the slot WAS released
        assert mock_slot.currentAgent is None

    def test_handle_logs_event_and_releases_slot_on_blocked(
        self, engine, mock_slot_factory
    ):
        """Standard Case: If an agent's outcome status is BLOCKED, the slot must be released."""
        mock_slot = mock_slot_factory(slot_id=1, current_agent="agent_1")
        outcome = (
            "BLOCKED",
            EventType.OPEN_BLOCKED,
            "Waiting for resource",
            ["agent_2"],
            "/tmp/lock",
        )

        engine.handle("agent_1", outcome, mock_slot, 25)

        # Verify the blocking event was logged
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 25
        assert actual_event.type == EventType.OPEN_BLOCKED
        assert actual_event.agent_id == "agent_1"
        assert actual_event.detail == "Waiting for resource"
        assert actual_event.related_agent_ids == ["agent_2"]
        assert actual_event.path == "/tmp/lock"

        # Verify the slot WAS released
        assert mock_slot.currentAgent is None

    def test_handle_edge_case_ignores_none_event_type(self, engine, mock_slot_factory):
        """Edge Case: Ensure handle properly processes an outcome even if the event_type is None."""
        mock_slot = mock_slot_factory(slot_id=1, current_agent="agent_1")
        # An agent advancing might not produce a distinct event this tick
        outcome = ("RUNNING", EventType.UNKNOWN_ERROR, "Executing compute", [], None)

        engine.handle("agent_1", outcome, mock_slot, 30)

        # Verify event was still created and logged (with None for type)
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 30
        assert actual_event.type is EventType.UNKNOWN_ERROR
        assert actual_event.agent_id == "agent_1"
        assert actual_event.detail == "Executing compute"

        # Verify the slot was NOT released
        assert mock_slot.currentAgent == "agent_1"


class TestSimulationEngineRunMethod:
    """Tests the full run() entry point of the SimulationEngine."""

    @patch("sys.exit")
    @patch("engine_SimulationEngine.EventLogger")
    @patch("engine_SimulationEngine.LockManager")
    @patch("engine_SimulationEngine.Scheduler")
    @patch("engine_SimulationEngine.VFS")
    @patch("engine_SimulationEngine.Agent")
    @patch("engine_SimulationEngine.json")
    @patch("builtins.open", new_callable=MagicMock)
    def test_run_initializes_and_executes_simulation_successfully(
        self,
        mock_open,
        mock_json,
        mock_agent_cls,
        mock_vfs_cls,
        mock_sched_cls,
        mock_lock_mgr_cls,
        mock_logger_cls,
        mock_sys_exit,
    ):
        """Standard Case: The run() method acts as a full factory and main loop for the application."""

        # 1. Provide Mock JSON Configuration
        mock_json.load.return_value = {
            "settings": {"max_running_agents": 4},
            "vfs": {
                "mounts": [{"source": "/host/dir", "target": "/vfs/mnt", "mode": "rw"}]
            },
            "agents": [
                {
                    "id": "ag_1",
                    "priority": 3,
                    "arrival_time": 0,
                    "path": "/scripts/op1.script",
                }
            ],
        }

        # Control the Mock Agent returned to assert exact state mutations
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance

        # Patch internal __init__ and tick() so we don't need real sub-system setups,
        # but can verify run() orchestrates the pieces precisely.
        with (
            patch.object(SimulationEngine, "__init__", return_value=None) as mock_init,
            patch.object(
                SimulationEngine, "tick", side_effect=[True, True, False]
            ) as mock_tick,
        ):
            # Execute Entry Point
            SimulationEngine.run("mocked_config.json")

            # Validate Step 1: Config Parsing
            mock_open.assert_any_call("mocked_config.json", "r")
            mock_json.load.assert_called_once()

            # Validate Step 2: VFS Construction & Mount Population
            mock_vfs_instance = mock_vfs_cls.return_value
            mock_vfs_instance.mount.assert_called_once_with(
                "/host/dir", "/vfs/mnt", "rw"
            )

            # Validate Step 3: Agent Initialization and Default Overrides
            mock_open.assert_any_call("/scripts/op1.script", "r")
            mock_agent_cls.assert_called_once_with(
                id="ag_1", priority=3, arrival_time=0, operations=ANY
            )

            # Assert initial properties strictly required by the prompt
            assert mock_agent_instance.state == AgentState.NEW
            assert mock_agent_instance.current_op_index == 0
            assert mock_agent_instance.start_time == -1
            assert mock_agent_instance.end_time == -1
            assert mock_agent_instance.wait_time == 0
            assert mock_agent_instance.blocked_time == 0
            assert mock_agent_instance.preemption_count == 0

            # Validate Step 4: Base Component Instantiation
            mock_lock_mgr_cls.assert_called_once()
            mock_logger_cls.assert_called_once()

            # Validate Step 5: Scheduler Construction
            mock_sched_cls.assert_called_once_with(4)

            # Validate Step 6: Engine Factory Wiring (Clock defaults to 0 implicitly)
            mock_init.assert_called_once_with(
                agents=[mock_agent_instance],
                scheduler=mock_sched_cls.return_value,
                logger=mock_logger_cls.return_value,
                vfs=mock_vfs_instance,
                lock_manager=mock_lock_mgr_cls.return_value,
            )

            # Validate Step 7: Tick Loop execution (3 calls to tick mock based on side_effect)
            assert mock_tick.call_count == 3

            # Validate Step 8: Final Logging call
            mock_logger_cls.return_value.printReport.assert_called_once()

            # Validate Step 9: Program termination hook
            mock_sys_exit.assert_called_once_with(0)

    @patch("sys.exit")
    @patch("engine_SimulationEngine.EventLogger")
    @patch("engine_SimulationEngine.LockManager")
    @patch("engine_SimulationEngine.Scheduler")
    @patch("engine_SimulationEngine.VFS")
    @patch("engine_SimulationEngine.Agent")
    @patch("engine_SimulationEngine.json")
    @patch("builtins.open", new_callable=MagicMock)
    def test_run_terminates_gracefully_with_empty_agents(
        self,
        mock_open,
        mock_json,
        mock_agent_cls,
        mock_vfs_cls,
        mock_sched_cls,
        mock_lock_mgr_cls,
        mock_logger_cls,
        mock_sys_exit,
    ):
        """Edge Case: Run successfully manages scenarios when no agents or mounts are configured."""

        # Empty configuration parameters
        mock_json.load.return_value = {
            "settings": {"max_running_agents": 2},
            "vfs": {"mounts": []},
            "agents": [],
        }

        with (
            patch.object(SimulationEngine, "__init__", return_value=None),
            patch.object(SimulationEngine, "tick", return_value=False) as mock_tick,
        ):
            SimulationEngine.run("empty_config.json")

            # Check logic handles the empty lists gracefully
            mock_vfs_cls.return_value.mount.assert_not_called()
            mock_agent_cls.assert_not_called()

            # Loop stops immediately on first return of False
            mock_tick.assert_called_once()

            # Report is printed regardless
            mock_logger_cls.return_value.printReport.assert_called_once()
            mock_sys_exit.assert_called_once_with(0)
