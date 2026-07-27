from src.logger_Event import Event


class EventLogger:
    def __init__(self):
        self.events = []

    def log(self, event):
        if not isinstance(event, Event):
            raise TypeError("Only Event objects can be logged.")
        self.events.append(event)

    def printReport(self):
        print("--- Simulation Event Report ---")
        for event in self.events:
            # We print the core attributes so they are captured by standard output
            print(
                f"[{event.time}] {event.agent_id} | {event.type.name} | {event.detail} | {event.path}"
            )
