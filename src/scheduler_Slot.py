class SlotInterval:
    def __init__(
        self, startTime: int, endTime: int | None = None, agentId: str | None = None
    ):
        if type(startTime) is not int:
            raise TypeError("startTime must be an integer.")
        if endTime is not None and type(endTime) is not int:
            raise TypeError("endTime must be an integer or None.")
        if agentId is not None and type(agentId) is not str:
            raise TypeError("agentId must be a string or None.")
        if endTime is not None and endTime < startTime:
            raise ValueError("endTime cannot be strictly less than startTime.")

        self._startTime = startTime
        self._endTime = endTime
        self._agentId = agentId

    @property
    def startTime(self) -> int:
        return self._startTime

    @property
    def agentId(self) -> str | None:
        return self._agentId

    @property
    def endTime(self) -> int | None:
        return self._endTime

    @endTime.setter
    def endTime(self, value: int | None):
        if value is not None and type(value) is not int:
            raise TypeError("endTime must be an integer or None.")
        if value is not None and value < self._startTime:
            raise ValueError("endTime cannot be strictly less than startTime.")
        self._endTime = value


class Slot:
    def __init__(self, id: int, currentAgent=None):
        if type(id) is not int:
            raise TypeError("id must be an integer.")
        self._id = id
        self.currentAgent = currentAgent
        self.history: list[SlotInterval] = []

    @property
    def id(self) -> int:
        return self._id

    @property
    def currentAgent(self):
        return self._currentAgent

    @currentAgent.setter
    def currentAgent(self, agent):
        if (
            agent is not None
            and getattr(getattr(agent, "__class__", None), "__name__", None) != "Agent"
        ):
            raise TypeError("currentAgent must be an Agent instance or None.")
        self._currentAgent = agent

    def openNewInterval(self, clock: int, agent_id: str | None = None) -> None:
        new_interval = SlotInterval(startTime=clock, endTime=None, agentId=agent_id)
        self.history.append(new_interval)

    def closeCurrentInterval(self, clock: int) -> None:
        # Explicit check added here so that clock values like `None`, strings, or floats are caught
        if type(clock) is not int:
            raise TypeError("clock must be an integer.")

        if not self.history:
            return

        self.history[-1].endTime = clock
