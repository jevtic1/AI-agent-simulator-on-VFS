import pytest
from scheduler_Scheduler import Scheduler

from models_Agent import Agent, AgentState


def create_test_agent(
    agent_id: str,
    priority: int,
    state: AgentState = AgentState.READY,
    preemption_count: int = 0,
) -> Agent:
    """Helper to instantiate a concrete Agent with given attributes."""
    agent = Agent(
        id=agent_id,
        priority=priority,
        arrival_time=0,
        operations=[],
    )
    agent.state = state
    agent.preemption_count = preemption_count
    return agent


@pytest.fixture
def empty_scheduler():
    """Provides a fresh Scheduler instance with 2 slots."""
    return Scheduler(maxRunningAgents=2)


class TestSchedulerInitialization:
    def test_scheduler_initialization(self):
        """Standard Case: Scheduler initializes with correct max agents, empty queue, and empty slots."""
        scheduler = Scheduler(maxRunningAgents=3)

        assert scheduler.maxRunningAgents == 3
        assert isinstance(scheduler.readyQueue, list)
        assert len(scheduler.readyQueue) == 0

        assert isinstance(scheduler.slots, list)
        assert len(scheduler.slots) == 3
        for slot in scheduler.slots:
            assert slot.currentAgent is None

    @pytest.mark.parametrize("invalid_max", [0, -1, "2", None])
    def test_initialization_invalid_max_agents(self, invalid_max):
        """Edge Case: maxRunningAgents must strictly be a positive integer."""
        with pytest.raises((ValueError, TypeError)):
            Scheduler(maxRunningAgents=invalid_max)


class TestSchedulerPreempt:
    @pytest.mark.parametrize("initial_preemption_count", [0, 1, 5])
    def test_preempt_agent_increments_preemption_count(
        self, empty_scheduler, initial_preemption_count
    ):
        """Standard Case: Preempting an agent transitions its state to READY,

        INCREMENTS preemption_count from its prior value, frees its slot, and re-queues it.
        """
        agent = create_test_agent(
            "A1",
            priority=5,
            state=AgentState.RUNNING,
            preemption_count=initial_preemption_count,
        )

        # Manually assign agent to slot for setup
        empty_scheduler.slots[0].currentAgent = agent

        empty_scheduler.preempt(agent)

        # 1. State changed to READY
        assert agent.state == AgentState.READY

        # 2. preemption_count strictly incremented (+1)
        assert agent.preemption_count == initial_preemption_count + 1

        # 3. Agent pushed back into readyQueue
        assert agent in empty_scheduler.readyQueue

        # 4. Slot is freed
        assert empty_scheduler.slots[0].currentAgent is None


class TestSchedulerScheduleNext:
    def test_schedule_next_empty_queue(self, empty_scheduler):
        """Edge Case: scheduleNext does nothing if readyQueue is empty."""
        empty_scheduler.scheduleNext()

        for slot in empty_scheduler.slots:
            assert slot.currentAgent is None

    def test_schedule_next_fills_empty_slots_by_priority(self, empty_scheduler):
        """Standard Case: Fills empty slots prioritizing agents with lower priority numbers."""
        agent1 = create_test_agent("A1", priority=10)
        agent2 = create_test_agent("A2", priority=1)  # Highest priority
        agent3 = create_test_agent("A3", priority=5)

        empty_scheduler.readyQueue.extend([agent1, agent2, agent3])

        empty_scheduler.scheduleNext()

        running_agents = [s.currentAgent for s in empty_scheduler.slots]

        # Highest priority agents (A2=1, A3=5) should be scheduled
        assert agent2 in running_agents
        assert agent3 in running_agents
        assert agent1 not in running_agents

        # A1 should remain in readyQueue
        assert agent1 in empty_scheduler.readyQueue
        assert len(empty_scheduler.readyQueue) == 1

        assert agent2.state == AgentState.RUNNING
        assert agent3.state == AgentState.RUNNING
        assert agent1.state == AgentState.READY

    def test_schedule_next_no_preemption_if_priority_worse_or_equal(
        self, empty_scheduler
    ):
        """Standard Case: When slots are full, ready agents with worse/equal priority do not cause preemption."""
        running1 = create_test_agent("R1", priority=2, state=AgentState.RUNNING)
        running2 = create_test_agent("R2", priority=3, state=AgentState.RUNNING)

        empty_scheduler.slots[0].currentAgent = running1
        empty_scheduler.slots[1].currentAgent = running2

        ready_worse = create_test_agent("W1", priority=5, state=AgentState.READY)
        ready_equal = create_test_agent("E1", priority=3, state=AgentState.READY)

        empty_scheduler.readyQueue.extend([ready_worse, ready_equal])

        empty_scheduler.scheduleNext()

        # Running agents remain untouched
        assert empty_scheduler.slots[0].currentAgent is running1
        assert empty_scheduler.slots[1].currentAgent is running2
        assert len(empty_scheduler.readyQueue) == 2

        assert running1.state == AgentState.RUNNING
        assert running2.state == AgentState.RUNNING
        assert ready_worse.state == AgentState.READY
        assert ready_equal.state == AgentState.READY

    def test_schedule_next_preempts_lowest_priority_running_agent(
        self, empty_scheduler
    ):
        """Standard Case: Preempts the lowest-priority running agent when a strictly higher-priority ready agent exists.

        Verifies preemption_count increment.
        """
        running_high_pri = create_test_agent("R1", priority=1, state=AgentState.RUNNING)

        initial_count = 3
        running_low_pri = create_test_agent(
            "R2", priority=10, state=AgentState.RUNNING, preemption_count=initial_count
        )

        empty_scheduler.slots[0].currentAgent = running_high_pri
        empty_scheduler.slots[1].currentAgent = running_low_pri

        ready_better = create_test_agent("B1", priority=5, state=AgentState.READY)
        empty_scheduler.readyQueue.append(ready_better)

        empty_scheduler.scheduleNext()

        running_agents = [s.currentAgent for s in empty_scheduler.slots]

        # R2 (priority 10) preempted in favor of B1 (priority 5)
        assert running_high_pri in running_agents
        assert ready_better in running_agents
        assert running_low_pri not in running_agents

        assert running_high_pri.state == AgentState.RUNNING
        assert ready_better.state == AgentState.RUNNING

        # R2 re-queued with updated state and incremented preemption count
        assert running_low_pri in empty_scheduler.readyQueue
        assert running_low_pri.state == AgentState.READY
        assert running_low_pri.preemption_count == initial_count + 1
