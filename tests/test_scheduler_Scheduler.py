from queue import PriorityQueue

import pytest

from models_Agent import Agent, AgentState
from scheduler_Scheduler import Scheduler


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
        # Ensure readyQueue is a PriorityQueue[cite: 12]
        assert isinstance(scheduler.readyQueue, PriorityQueue)
        assert scheduler.readyQueue.qsize() == 0

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

        # 3. Agent pushed back into readyQueue as a tuple: (priority, counter, agent)[cite: 12]
        assert any(agent == item[2] for item in empty_scheduler.readyQueue.queue)

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

        # Using PriorityQueue.put() with structure: (priority, insertion_counter, agent)[cite: 12]
        empty_scheduler.readyQueue.put((agent1.priority, 1, agent1))
        empty_scheduler.readyQueue.put((agent2.priority, 2, agent2))
        empty_scheduler.readyQueue.put((agent3.priority, 3, agent3))

        empty_scheduler.scheduleNext()

        running_agents = [s.currentAgent for s in empty_scheduler.slots]

        # Highest priority agents (A2=1, A3=5) should be scheduled
        assert agent2 in running_agents
        assert agent3 in running_agents
        assert agent1 not in running_agents

        # A1 should remain in readyQueue[cite: 12]
        assert any(agent1 == item[2] for item in empty_scheduler.readyQueue.queue)
        assert empty_scheduler.readyQueue.qsize() == 1

        assert agent2.state == AgentState.RUNNING
        assert agent3.state == AgentState.RUNNING
        assert agent1.state == AgentState.READY

    def test_schedule_next_fifo_for_same_priority(self, empty_scheduler):
        """Standard Case: Agents with identical priorities are scheduled in strict FIFO order."""
        agent1 = create_test_agent("A1", priority=5)
        agent2 = create_test_agent("A2", priority=5)
        agent3 = create_test_agent("A3", priority=5)

        # Inserting same priorities; insertion counter determines tie-breaking FIFO order[cite: 12]
        empty_scheduler.readyQueue.put((agent1.priority, 1, agent1))
        empty_scheduler.readyQueue.put((agent2.priority, 2, agent2))
        empty_scheduler.readyQueue.put((agent3.priority, 3, agent3))

        empty_scheduler.scheduleNext()

        running_agents = [s.currentAgent for s in empty_scheduler.slots]

        # A1 and A2 arrived first (counters 1 and 2), so they must be scheduled before A3[cite: 12]
        assert agent1 in running_agents
        assert agent2 in running_agents
        assert agent3 not in running_agents

        assert agent1.state == AgentState.RUNNING
        assert agent2.state == AgentState.RUNNING
        assert agent3.state == AgentState.READY

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

        # Enqueue with structure: (priority, counter, agent)[cite: 12]
        empty_scheduler.readyQueue.put((ready_worse.priority, 1, ready_worse))
        empty_scheduler.readyQueue.put((ready_equal.priority, 2, ready_equal))

        empty_scheduler.scheduleNext()

        # Running agents remain untouched
        assert empty_scheduler.slots[0].currentAgent is running1
        assert empty_scheduler.slots[1].currentAgent is running2
        assert empty_scheduler.readyQueue.qsize() == 2

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
        empty_scheduler.readyQueue.put((ready_better.priority, 1, ready_better))

        empty_scheduler.scheduleNext()

        running_agents = [s.currentAgent for s in empty_scheduler.slots]

        # R2 (priority 10) preempted in favor of B1 (priority 5)
        assert running_high_pri in running_agents
        assert ready_better in running_agents
        assert running_low_pri not in running_agents

        assert running_high_pri.state == AgentState.RUNNING
        assert ready_better.state == AgentState.RUNNING

        # R2 re-queued with updated state and incremented preemption count
        assert any(
            running_low_pri == item[2] for item in empty_scheduler.readyQueue.queue
        )
        assert running_low_pri.state == AgentState.READY
        assert running_low_pri.preemption_count == initial_count + 1


class TestSchedulerEnqueueReadyAgent:
    def test_enqueue_single_agent(self, empty_scheduler):
        """Standard Case: Enqueueing an agent places it in the queue with the correct tuple structure."""
        agent = create_test_agent("A1", priority=5)

        # Action
        empty_scheduler.enqueue_ready_agent(agent)

        # Assertions
        assert empty_scheduler.readyQueue.qsize() == 1

        # Peek at the queued item directly in the underlying list[cite: 12]
        queued_item = empty_scheduler.readyQueue.queue[0]
        assert isinstance(queued_item, tuple)
        assert len(queued_item) == 3
        assert queued_item[0] == 5  # priority
        assert queued_item[2] is agent  # agent strictly stored as object[cite: 12]

    def test_enqueue_increments_counter_to_prevent_ties(self, empty_scheduler):
        """Standard Case: Enqueueing multiple agents strictly increments the internal counter."""
        agent1 = create_test_agent("A1", priority=5)
        agent2 = create_test_agent("A2", priority=5)

        empty_scheduler.enqueue_ready_agent(agent1)
        empty_scheduler.enqueue_ready_agent(agent2)

        assert empty_scheduler.readyQueue.qsize() == 2

        # Extract items from the internal queue array[cite: 12]
        items = empty_scheduler.readyQueue.queue

        # Locate the insertion counters (index 1 of the tuple) for each agent
        counter1 = next(item[1] for item in items if item[2] is agent1)
        counter2 = next(item[1] for item in items if item[2] is agent2)

        # The agent added second MUST have a higher insertion counter[cite: 12]
        assert counter1 < counter2

    def test_enqueue_maintains_priority_and_fifo_order(self, empty_scheduler):
        """Standard Case: The PriorityQueue correctly pops agents by priority, falling back to FIFO via the counter."""
        agent_low_pri = create_test_agent("LowPri", priority=10)
        agent_high_pri = create_test_agent("HighPri", priority=1)
        agent_tie_1 = create_test_agent("Tie1", priority=5)
        agent_tie_2 = create_test_agent("Tie2", priority=5)

        # Enqueue in a mixed, non-sorted order
        empty_scheduler.enqueue_ready_agent(agent_low_pri)
        empty_scheduler.enqueue_ready_agent(agent_tie_1)  # Arrives first
        empty_scheduler.enqueue_ready_agent(agent_high_pri)
        empty_scheduler.enqueue_ready_agent(agent_tie_2)  # Arrives second

        # Dequeue using the PriorityQueue's built-in get() to verify sorting behavior[cite: 12]
        popped_1 = empty_scheduler.readyQueue.get()[2]
        popped_2 = empty_scheduler.readyQueue.get()[2]
        popped_3 = empty_scheduler.readyQueue.get()[2]
        popped_4 = empty_scheduler.readyQueue.get()[2]

        # 1. Highest priority (lowest integer)
        assert popped_1 is agent_high_pri

        # 2 & 3. Ties should be strictly resolved by FIFO (Tie1 was enqueued before Tie2)[cite: 12]
        assert popped_2 is agent_tie_1
        assert popped_3 is agent_tie_2

        # 4. Lowest priority (highest integer)
        assert popped_4 is agent_low_pri

        assert empty_scheduler.readyQueue.qsize() == 0

    def test_enqueue_already_queued_agent_is_ignored(self, empty_scheduler):
        """Edge Case: Enqueueing an agent that is already in the readyQueue does not create duplicates."""
        agent = create_test_agent("A1", priority=5)

        # Enqueue the first time
        empty_scheduler.enqueue_ready_agent(agent)
        assert empty_scheduler.readyQueue.qsize() == 1

        # Attempt to enqueue the exact same agent again
        empty_scheduler.enqueue_ready_agent(agent)

        # Queue size should remain 1 to prevent duplicate execution loops
        assert empty_scheduler.readyQueue.qsize() == 1

        # Double-check the underlying list to ensure only one reference exists
        items = empty_scheduler.readyQueue.queue
        occurrences = sum(1 for item in items if item[2] is agent)
        assert occurrences == 1
