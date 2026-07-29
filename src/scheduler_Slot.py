class Slot:
    def __init__(self, id: int, currentAgent=None):
        if type(id) is not int:
            raise TypeError("id must be an integer.")
        self._id = id
        self.currentAgent = currentAgent

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
