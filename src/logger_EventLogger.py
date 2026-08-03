from src.logger_Event import Event


class EventLogger:
    def __init__(self):
        self.events = []

    def log(self, event):
        if not isinstance(event, Event):
            raise TypeError("Only Event objects can be logged.")
        self.events.append(event)

    def printReport(self, agents, slots, vfs):
        print("--- Simulation Event Report ---")
        for event in self.events:
            # We print the core attributes so they are captured by standard output
            print(
                f"[{event.time}] {event.agent_id} | {event.type.name} | {event.detail} | {event.path}"
            )

        # Call summary for each slot
        print("=" * 28 + " Gantova karta " + "=" * 28)
        for slot in slots:
            print(slot.gantt_row())

        # Call summary for each agent
        print("=" * 25 + " Zavrsno stanje agenata " + "=" * 25)
        print(
            f"{'ID':<7} {'Status':<11} {'Arrival':<9} {'Start':<8} {'End':<5} {'Wait':<8} {'Blocked':<10} {'Preempts':<13}"
        )
        for agent in agents:
            print(agent.report_row())

        # Call snapshot on the virtual file system
        print("=" * 25 + " Zavrsno stanje VFS-a " + "=" * 25)
        print(vfs.snapshot())
        print("=" * 78)
