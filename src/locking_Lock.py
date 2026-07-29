class Lock:
    def __init__(self, path: str, type: str):
        if not isinstance(path, str) or not path:
            raise ValueError("Path must be a non-empty string.")

        self.path = path
        # Assigning to self.type triggers the property setter validation
        self.type = type
        self.holders = []
        self.waiters = []

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in ("shared", "exclusive"):
            raise ValueError("Type must strictly be 'shared' or 'exclusive'.")
        self._type = value
