import heapq
from queue import PriorityQueue
from typing import List, Tuple

from models_Agent import Agent, AgentState


class Slot:
    """Helper class to represent an execution slot."""

    def __init__(self, slot_id: int):
        self.id = slot_id
        self.currentAgent: Agent = None


class Scheduler:
    def __init__(self, maxRunningAgents: int):
        if not isinstance(maxRunningAgents, int) or maxRunningAgents <= 0:
            raise ValueError("maxRunningAgents must strictly be a positive integer.")

        self.maxRunningAgents = maxRunningAgents
        self.readyQueue = PriorityQueue()
        self.slots = [Slot(i) for i in range(maxRunningAgents)]
        self._counter = 0

    def enqueue_ready_agent(self, agent: Agent) -> None:
        """Adds an agent to the readyQueue, preventing duplicates and ensuring FIFO for ties."""
        # Prevent duplicates
        if any(item[2] is agent for item in self.readyQueue.queue):
            return

        # Keep counters small: Reset if the queue is completely empty
        if self.readyQueue.empty():
            self._counter = 0

        self._counter += 1
        # Store as (priority, counter, agent)
        self.readyQueue.put((agent.priority, self._counter, agent))

    def dequeue_agent(self, agent: Agent) -> bool:
        """Finds and removes the specified agent reference from the readyQueue."""
        target_tuple = None
        for item in self.readyQueue.queue:
            if item[2] is agent:
                target_tuple = item
                break

        if target_tuple is None:
            return False

        self.readyQueue.queue.remove(target_tuple)
        heapq.heapify(self.readyQueue.queue)

        return True

    def preempt(self, agent: Agent) -> None:
        """Preempts a running agent, updates its state, frees its slot, and re-queues it."""
        agent.state = AgentState.READY
        agent.preemption_count += 1

        for slot in self.slots:
            if slot.currentAgent is agent:
                slot.currentAgent = None
                break

        self.enqueue_ready_agent(agent)

    def scheduleNext(self) -> List[Tuple[str, int, bool]]:
        """Fills empty slots and preempts lower priority agents if better ones are ready."""
        assignments = []

        # 1. Fill empty slots first
        for slot in self.slots:
            if slot.currentAgent is None and not self.readyQueue.empty():
                _, _, next_agent = self.readyQueue.get()
                next_agent.state = AgentState.RUNNING
                slot.currentAgent = next_agent
                assignments.append((next_agent.id, slot.id, False))

        # 2. Preempt worst running agents if higher priority agents are in queue
        while not self.readyQueue.empty():
            # Find the running agent with the worst (highest) priority number
            worst_slot = max(
                self.slots,
                key=lambda s: s.currentAgent.priority if s.currentAgent else -1,
            )

            if worst_slot.currentAgent is None:
                break

            best_ready_priority = self.readyQueue.queue[0][0]

            if best_ready_priority < worst_slot.currentAgent.priority:
                # Preempt worst
                self.preempt(worst_slot.currentAgent)

                # Assign the best ready agent to the newly freed slot
                _, _, best_agent = self.readyQueue.get()
                best_agent.state = AgentState.RUNNING
                worst_slot.currentAgent = best_agent
                assignments.append((best_agent.id, worst_slot.id, True))
            else:
                break  # No higher priority agents left to cause a preemption

        return assignments
