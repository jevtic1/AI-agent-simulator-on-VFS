from models_Agent import AgentState
from scheduler_Slot import Slot


class Scheduler:
    def __init__(self, maxRunningAgents):
        # maxRunningAgents must be strictly a positive integer
        if type(maxRunningAgents) is not int:
            raise TypeError("maxRunningAgents must be an integer")
        if maxRunningAgents <= 0:
            raise ValueError("maxRunningAgents must be positive")

        self.maxRunningAgents = maxRunningAgents
        self.readyQueue = []
        self.slots = [Slot(i) for i in range(maxRunningAgents)]

    def preempt(self, agent):
        """Preempts an agent, updates its state, increments preemption count, and frees its slot."""
        agent.state = AgentState.READY
        agent.preemption_count += 1
        self.readyQueue.append(agent)

        for slot in self.slots:
            if slot.currentAgent is agent:
                slot.currentAgent = None

    def scheduleNext(self):
        """Schedules highest priority ready agents into empty slots, preempting lowest priority running agents if necessary."""
        if not self.readyQueue:
            return

        # Sort the queue so lower numbers (higher priorities) are first
        self.readyQueue.sort(key=lambda a: a.priority)

        made_progress = True
        while self.readyQueue and made_progress:
            made_progress = False

            # Look for an empty slot
            empty_slot = next((s for s in self.slots if s.currentAgent is None), None)

            if empty_slot:
                agent = self.readyQueue.pop(0)
                agent.state = AgentState.RUNNING
                empty_slot.currentAgent = agent
                made_progress = True
            else:
                # If slots are full, find the running agent with the lowest priority (highest number)[cite: 1]
                worst_slot = max(self.slots, key=lambda s: s.currentAgent.priority)
                worst_agent = worst_slot.currentAgent
                best_ready_agent = self.readyQueue[0]

                # Preempt only if the ready agent has strictly better priority[cite: 1]
                if best_ready_agent.priority < worst_agent.priority:
                    self.preempt(worst_agent)
                    # Re-sort to account for the newly appended preempted agent[cite: 1]
                    self.readyQueue.sort(key=lambda a: a.priority)
                    made_progress = True
