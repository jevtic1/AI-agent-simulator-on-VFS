from unittest.mock import MagicMock, patch

import pytest

# Dependencies based on provided system specifications
from src.engine_SimulationEngine import SimulationEngine
from src.logger_Event import Event, EventType
from src.models_Agent import Agent, AgentState


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
    """Helper fixture to create mocked Agents with all time-tracking attributes."""

    def _create_agent(agent_id, arrival_time, state=AgentState.NEW):
        agent = MagicMock(spec=Agent)
        agent.id = agent_id
        agent.priority = 2
        agent.arrival_time = arrival_time
        agent.state = state
        agent.start_time = -1
        agent.end_time = -1
        agent.wait_time = 0
        agent.blocked_time = 0
        agent.preemption_count = 0
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
    """Tests the Phase 1, Phase 2, STATS, Phase 3, and return rules of the tick() method."""

    def test_tick_phase1_arrivals_enqueues_correct_agents(
        self,
        engine,
        mock_scheduler,
        mock_logger,
        mock_agent,
    ):
        """Standard Case: NEW Agents arriving at the current clock get enqueued and logged.
        Additional Case: Agents already in READY state should also be enqueued."""
        engine.clock = 5
        agent_arriving = mock_agent("agent_new", arrival_time=5, state=AgentState.NEW)
        agent_future = mock_agent("agent_future", arrival_time=10, state=AgentState.NEW)
        agent_ready = mock_agent("agent_ready", arrival_time=1, state=AgentState.READY)

        engine.agents = [agent_arriving, agent_future, agent_ready]

        engine.tick()

        # Check Phase 1 operations for the newly arrived agent
        assert agent_arriving.state == AgentState.READY

        # Verify both the newly arrived agent and the previously READY agent are enqueued
        assert mock_scheduler.enqueue_ready_agent.call_count == 2
        mock_scheduler.enqueue_ready_agent.assert_any_call(agent_arriving)
        mock_scheduler.enqueue_ready_agent.assert_any_call(agent_ready)

        # Verify the arrival event was logged for the newly arrived agent
        actual_event = mock_logger.log.call_args[0][0]
        assert actual_event.time == 5
        assert actual_event.type == EventType.AGENT_ARRIVED
        assert actual_event.agent_id == "agent_new"

        # The future agent should be ignored this tick
        assert agent_future.state == AgentState.NEW

    def test_tick_phase2_scheduling_assigns_slots_and_logs(
        self,
        engine,
        mock_scheduler,
        mock_logger,
        mock_agent,
        mock_slot_factory,
    ):
        """Standard Case: newlyAssigned agents have their intervals updated on the slot.
        start_time is initialized if it was previously -1."""
        engine.clock = 5

        # Setup newly assigned pair
        mock_agent_instance = mock_agent("agent_X", arrival_time=0)
        mock_agent_instance.start_time = -1

        mock_slot = mock_slot_factory(slot_id=0, current_agent=mock_agent_instance)

        # scheduleNext returns the newly assigned tuple: (Agent, Slot, PreemptedAgent)
        mock_scheduler.scheduleNext.return_value = [
            (mock_agent_instance, mock_slot, None)
        ]

        engine.tick()

        # Phase 2 Validation: start_time updated to current clock
        assert mock_agent_instance.start_time == 5

        # Slot metrics should be finalized for prior state and opened for new agent
        mock_slot.closeCurrentInterval.assert_called_once_with(engine.clock - 1)
        mock_slot.openNewInterval.assert_called_once_with(engine.clock - 1, "agent_X")

        # Must log the slot assignment
        actual_event = mock_logger.log.call_args[0][0]
        assert actual_event.time == 5
        assert actual_event.type == EventType.SLOT_ASSIGNED
        assert actual_event.agent_id == "agent_X"

    def test_tick_phase2_scheduling_increments_preempted_agent_count(
        self, engine, mock_scheduler, mock_agent, mock_slot_factory
    ):
        """Standard Case: If a preempt_agent is present in the scheduleNext tuple,
        its preemption_count must be incremented."""
        engine.clock = 5

        # Setup agents
        mock_agent_instance = mock_agent("agent_HIGH", arrival_time=0)
        mock_preempted_agent = mock_agent("agent_LOW", arrival_time=0)
        mock_preempted_agent.preemption_count = 1

        mock_slot = mock_slot_factory(slot_id=0, current_agent=mock_agent_instance)

        # Return a preempted agent as the third element
        mock_scheduler.scheduleNext.return_value = [
            (mock_agent_instance, mock_slot, mock_preempted_agent)
        ]

        engine.tick()

        # Preemption count must be incremented for the preempted agent
        assert mock_preempted_agent.preemption_count == 2

    def test_tick_stats_phase_updates_wait_and_blocked_times(self, engine, mock_agent):
        """Standard Case: STATS phase correctly increments wait_time for READY agents
        and blocked_time for BLOCKED agents."""
        engine.clock = 5
        agent_ready = mock_agent("r1", arrival_time=0, state=AgentState.READY)
        agent_blocked = mock_agent("b1", arrival_time=0, state=AgentState.BLOCKED)
        agent_running = mock_agent("run1", arrival_time=0, state=AgentState.RUNNING)

        engine.agents = [agent_ready, agent_blocked, agent_running]

        # Ensure initial states
        assert agent_ready.wait_time == 0
        assert agent_blocked.blocked_time == 0

        engine.tick()

        # wait_time should increase by 1 for READY agents
        assert agent_ready.wait_time == 1
        assert agent_ready.blocked_time == 0

        # blocked_time should increase by 1 for BLOCKED agents
        assert agent_blocked.wait_time == 0
        assert agent_blocked.blocked_time == 1

        # RUNNING agent time counters remain unaffected by STATS phase
        assert agent_running.wait_time == 0
        assert agent_running.blocked_time == 0

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
        mock_scheduler.scheduleNext.return_value = [(new_agent, new_slot, None)]

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
        self, engine, mock_slot_factory, mock_agent
    ):
        """Standard Case: A successful/pending agent execution logs an event but remains in the slot."""
        mock_agent_instance = mock_agent(
            "agent_1", arrival_time=0, state=AgentState.RUNNING
        )
        mock_slot = mock_slot_factory(slot_id=1, current_agent=mock_agent_instance)
        # outcome tuple structure: (status, event_type, detail, related_agent_ids, path)
        outcome = (
            "SUCCESS",
            EventType.READ_DONE,
            "File read successfully",
            [],
            None,
        )

        engine.handle(mock_agent_instance, outcome, mock_slot, 15)

        # Verify the event was correctly parsed and logged
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 15
        assert actual_event.type == EventType.READ_DONE
        assert actual_event.agent_id == "agent_1"
        assert actual_event.detail == "File read successfully"
        assert actual_event.related_agent_ids == []
        assert actual_event.path is None

        # Verify the slot was NOT released
        assert mock_slot.currentAgent == mock_agent_instance

    def test_handle_removes_agent_from_slot_if_state_is_terminated(
        self, engine, mock_slot_factory, mock_agent
    ):
        """Standard Case: If an agent's state is TERMINATED, the slot must be released, event logged, and end_time set."""
        mock_agent_instance = mock_agent(
            "agent_1", arrival_time=0, state=AgentState.TERMINATED
        )
        mock_slot = mock_slot_factory(slot_id=1, current_agent=mock_agent_instance)
        outcome = (
            "TERMINATED",
            EventType.AGENT_TERMINATED,
            "Agent completed operations",
            [],
            None,
        )

        engine.handle(mock_agent_instance, outcome, mock_slot, 20)

        # Verify the completion event was logged since EventType is not None
        actual_event = engine.logger.log.call_args[0][0]
        assert actual_event.time == 20
        assert actual_event.type == EventType.AGENT_TERMINATED
        assert actual_event.agent_id == "agent_1"

        # Verify the slot WAS released because the state is TERMINATED
        assert mock_slot.currentAgent is None

        # Verify that end_time was correctly recorded to the clock time passed to handle()
        assert mock_agent_instance.end_time == 20

    def test_handle_logs_event_and_releases_slot_on_blocked(
        self, engine, mock_slot_factory, mock_agent
    ):
        """Standard Case: If an agent is BLOCKED, the slot must be released."""
        mock_agent_instance = mock_agent(
            "agent_1", arrival_time=0, state=AgentState.BLOCKED
        )
        mock_slot = mock_slot_factory(slot_id=1, current_agent=mock_agent_instance)
        outcome = (
            "BLOCKED",
            EventType.OPEN_BLOCKED,
            "Waiting for resource",
            ["agent_2"],
            "/tmp/lock",
        )

        engine.handle(mock_agent_instance, outcome, mock_slot, 25)

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

    def test_handle_does_not_log_if_outcome_type_is_none(
        self, engine, mock_slot_factory, mock_agent
    ):
        """Edge Case: Ensure handle does not log an event if the event_type (second item) is None."""
        mock_agent_instance = mock_agent(
            "agent_1", arrival_time=0, state=AgentState.RUNNING
        )
        mock_slot = mock_slot_factory(slot_id=1, current_agent=mock_agent_instance)
        # outcome tuple structure: (status, event_type, detail, related_agent_ids, path)
        outcome = ("RUNNING", None, "Executing compute", [], None)

        engine.handle(mock_agent_instance, outcome, mock_slot, 30)

        # Verify event logger was NOT called since EventType is None
        engine.logger.log.assert_not_called()

        # Verify the slot was NOT released
        assert mock_slot.currentAgent == mock_agent_instance


class TestSimulationEngineRunMethod:
    """Tests the full run() entry point of the SimulationEngine using the Parser class."""

    @patch("sys.exit")
    @patch("src.engine_SimulationEngine.EventLogger")
    @patch("src.engine_SimulationEngine.LockManager")
    @patch("src.engine_SimulationEngine.Scheduler")
    @patch("src.engine_SimulationEngine.VFS")
    @patch("src.engine_SimulationEngine.Parser")
    def test_run_initializes_and_executes_simulation_successfully(
        self,
        mock_parser_cls,
        mock_vfs_cls,
        mock_sched_cls,
        mock_lock_mgr_cls,
        mock_logger_cls,
        mock_sys_exit,
    ):
        """Standard Case: run() uses Parser to get the Config, builds the components, and loops the simulation."""

        # 1. Setup Mock Config returned by the Parser
        mock_mount = MagicMock()
        mock_mount.source = "/host/dir"
        mock_mount.target = "/vfs/mnt"
        mock_mount.mode = "rw"

        mock_agent_instance = MagicMock()

        mock_config = MagicMock()
        mock_config.max_running_agents = 4
        mock_config.mounts = [mock_mount]
        mock_config.agents = [mock_agent_instance]

        mock_parser_cls.parse_file.return_value = mock_config

        # 2. Patch __init__ and tick() to control execution flow without needing real implementations
        with (
            patch.object(SimulationEngine, "__init__", return_value=None) as mock_init,
            patch.object(
                SimulationEngine, "tick", side_effect=[True, True, False]
            ) as mock_tick,
        ):
            # Execute Entry Point
            SimulationEngine.run("mocked_config.json")

            # Validate Step 1: Config Parsing delegates to Parser
            mock_parser_cls.parse_file.assert_called_once_with("mocked_config.json")

            # Validate Step 2: VFS Construction & Mount Population using Config properties
            mock_vfs_instance = mock_vfs_cls.return_value
            mock_vfs_instance.mount.assert_called_once_with(
                "/host/dir", "/vfs/mnt", "rw"
            )

            # Validate Step 3: Agent Initialization explicitly overriding start states
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

            # Validate Step 5: Scheduler Construction uses max_running_agents from Config
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

            # Validate Step 8: Final Logging call with agents, slots, and vfs references
            mock_logger_cls.return_value.printReport.assert_called_once_with(
                mock_config.agents, mock_sched_cls.return_value.slots, mock_vfs_instance
            )

            # Validate Step 9: Program termination hook
            mock_sys_exit.assert_called_once_with(0)

    @patch("sys.exit")
    @patch("src.engine_SimulationEngine.EventLogger")
    @patch("src.engine_SimulationEngine.LockManager")
    @patch("src.engine_SimulationEngine.Scheduler")
    @patch("src.engine_SimulationEngine.VFS")
    @patch("src.engine_SimulationEngine.Parser")
    def test_run_terminates_gracefully_with_empty_config(
        self,
        mock_parser_cls,
        mock_vfs_cls,
        mock_sched_cls,
        mock_lock_mgr_cls,
        mock_logger_cls,
        mock_sys_exit,
    ):
        """Edge Case: Run successfully manages scenarios when no agents or mounts are present in the parsed Config."""

        # Setup an empty mock Config
        mock_config = MagicMock()
        mock_config.max_running_agents = 2
        mock_config.mounts = []
        mock_config.agents = []
        mock_parser_cls.parse_file.return_value = mock_config

        with (
            patch.object(SimulationEngine, "__init__", return_value=None),
            patch.object(SimulationEngine, "tick", return_value=False) as mock_tick,
        ):
            SimulationEngine.run("empty_config.json")

            # Check logic handles the empty lists gracefully
            mock_vfs_cls.return_value.mount.assert_not_called()

            # Loop stops immediately on first return of False
            mock_tick.assert_called_once()

            # Report is printed regardless with agents, slots, and vfs references
            mock_logger_cls.return_value.printReport.assert_called_once_with(
                mock_config.agents,
                mock_sched_cls.return_value.slots,
                mock_vfs_cls.return_value,
            )
            mock_sys_exit.assert_called_once_with(0)
