import sys

from src.locking_LockManager import LockManager
from src.logger_Event import Event, EventType
from src.logger_EventLogger import EventLogger
from src.models_Agent import AgentState
from src.scheduler_Scheduler import Scheduler
from src.util_Parser import Parser
from src.vfs_VFS import VFS


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

                # Log the arrival
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

        for agent, slot, is_preemptible in new_assignments:
            # Look up the actual Slot and Agent objects by ID
            slot = next((s for s in self.scheduler.slots if s.id == slot.id), None)
            agent = next((a for a in self.agents if a.id == agent.id), None)

            slot.closeCurrentInterval(self.clock)
            slot.openNewInterval(self.clock, agent.id)

            # Log the assignment
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
                agent = slot.currentAgent
                if agent.id not in newly_assigned_agents:
                    outcome = slot.currentAgent.advance(self.vfs, self.lock_manager)
                    self.handle(agent, outcome, slot, self.clock)

        self.clock += 1
        return True

    def handle(self, agent, outcome, slot, clock):
        # 1. Unpack outcome tuple
        if outcome is None:
            print("VRACEN NONE! POPRAVI")
            return

        status, event_type, detail, related_agent_ids, path = outcome
        agent_id = agent if isinstance(agent, str) else agent.id

        # 2. Log event
        event = Event(
            time=clock,
            type=event_type,
            agent_id=agent_id,
            detail=detail,
            related_agent_ids=related_agent_ids,
            path=path,
        )
        self.logger.log(event)

        # 3. Release slot if agent blocked or terminated
        if status in ("TERMINATED", "BLOCKED"):
            slot.currentAgent = None

    @classmethod
    def run(cls, config_path: str):
        """Entry point: parses config, constructs environment, loops tick(), prints report, and exits."""
        # 1. Parse JSON configuration
        config = Parser.parse_file(config_path)

        # 2. Construct VFS and mount files
        vfs = VFS()
        for mount in config.mounts:
            vfs.mount(mount.source, mount.target, mount.mode)

        # 3. Ensure agent initial metrics and states are set
        for agent in config.agents:
            agent.state = AgentState.NEW
            agent.current_op_index = 0
            agent.start_time = -1
            agent.end_time = -1
            agent.wait_time = 0
            agent.blocked_time = 0
            agent.preemption_count = 0

        # 4 & 5. Instantiate core services
        lock_manager = LockManager()
        logger = EventLogger()
        scheduler = Scheduler(config.max_running_agents)

        # 6. Wire SimulationEngine
        engine = cls(
            agents=config.agents,
            scheduler=scheduler,
            logger=logger,
            vfs=vfs,
            lock_manager=lock_manager,
        )

        # 7. Execution loop until all agents complete
        while engine.tick():
            pass

        # 8 & 9. Output report and terminate program
        logger.printReport()
        sys.exit(0)


if __name__ == "__main__":
    # Standard CLI usage: python engine_SimulationEngine.py path/to/config.json
    # Fallback usage (Double-click): defaults to "config.json" in the same directory
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    SimulationEngine.run(config_file)
