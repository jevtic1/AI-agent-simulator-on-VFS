from logger_Event import Event, EventType
from models_Agent import AgentState


class SimulationEngine:
    def __init__(self, agents, scheduler, logger, vfs, lock_manager):
        """Initializes the SimulationEngine with provided dependencies."""
        self.agents = agents
        self.scheduler = scheduler
        self.logger = logger
        self.vfs = vfs
        self.lock_manager = lock_manager
        self.clock = 0

    def tick(self) -> bool:
        """Executes a single tick of the simulation, consisting of 3 phases."""

        # Return Condition: Stop if all agents are TERMINATED
        if self.agents and all(
            agent.state == AgentState.TERMINATED for agent in self.agents
        ):
            return False

        # Phase 1: Arrivals
        for agent in self.agents:
            if agent.state == AgentState.NEW and agent.arrival_time == self.clock:
                agent.state = AgentState.READY
                self.scheduler.enqueue_ready_agent(agent)

                # Log the arrival - detail argument added to satisfy the constructor
                event = Event(
                    time=self.clock,
                    type=EventType.AGENT_ARRIVED,
                    agent_id=agent.id,
                    detail=f"Agent {agent.id} stigao, prioritet={agent.priority}\n",
                )
                self.logger.log(event)

        # Phase 2: Scheduling
        new_assignments = self.scheduler.scheduleNext()
        newly_assigned_agents = set()

        for slot, agent in new_assignments:
            slot.closeCurrentInterval(self.clock)
            slot.openNewInterval(self.clock, agent.id)

            # Log the assignment scheduling - detail argument added to satisfy the constructor
            event = Event(
                time=self.clock,
                type=EventType.SLOT_ASSIGNED,
                agent_id=agent.id,
                detail=f"{slot.id} <- {agent.id}",
            )
            self.logger.log(event)

            newly_assigned_agents.add(agent.id)

        # Phase 3: Execution
        for slot in self.scheduler.slots:
            if slot.currentAgent is not None:
                # Newly assigned agents in Phase 2 must NOT advance in the same tick
                agent = slot.currentAgent
                if agent.id not in newly_assigned_agents:
                    # Existing agents are advanced
                    outcome = slot.currentAgent.advance(self.vfs, self.lock_manager)
                    self.handle(agent.id, outcome, slot, self.clock)

        self.clock += 1
        return True

    def handle(self, agent_id, outcome, slot, clock):
        """Internal handler for processing the result of an agent's advance() step."""
        pass

    def run(self):
        """Primary execution loop that runs until tick() evaluates to False."""
        while self.tick():
            pass
