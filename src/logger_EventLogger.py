from src.logger_Event import Event, EventType
from src.models_Agent import Agent


class EventLogger:
    def __init__(self):
        self.events = []

    def log(self, event):
        if not isinstance(event, Event):
            raise TypeError("Only Event objects can be logged.")
        self.events.append(event)

    def printReport(self, agents, slots, vfs):
        print("=" * 28 + " DNEVNIK DOGADJAJA " + "=" * 28)

        rejection_counter = 0
        for event in self.events:
            if event.type == EventType.OPEN_REJECTED:
                rejection_counter += 1
            # We print the core attributes so they are captured by standard output
            print(f"[{event.time}] {event.detail}")

        # Call summary for each slot
        print("=" * 28 + " Gantova karta " + "=" * 31)
        for slot in slots:
            print(slot.gantt_row())

        # Call summary for each agent
        print("=" * 25 + " Zavrsno stanje agenata " + "=" * 25)
        print(
            f"{'ID':<7} {'Status':<11} {'Arrival':<9} {'Start':<8} {'End':<5} {'Wait':<8} {'Blocked':<10} {'Preempts':<13}"
        )
        for agent in agents:
            print(agent.report_row())

        # Call rejections report
        print("=" * 25 + " Odbijena zakljucavanja " + "=" * 25)
        open_rejected_events = self.get_open_rejected_events()
        if open_rejected_events == "":
            print("Nema odbijenih zakljucavanja.")
        else:
            print(open_rejected_events)

        # Call snapshot on the virtual file system
        print("=" * 26 + " Zavrsno stanje VFS-a " + "=" * 26)
        print(vfs.snapshot())

        # Call average stats method from Agent class
        print("=" * 31 + " Statistika " + "=" * 31)
        print(f"Broj sprijecenih zastoja: {rejection_counter}")
        print(Agent.calculate_average_stats())
        print("=" * 74)

    def get_open_rejected_events(self) -> str:
        """Returns a formatted string containing only the OPEN_REJECTED events."""
        rejected_events = [
            f"[{event.time}] {event.detail}"
            for event in self.events
            if event.type == EventType.OPEN_REJECTED
        ]
        return "\n".join(rejected_events)
