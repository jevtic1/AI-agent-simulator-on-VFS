class Lock:
    def __init__(self, path: str, type: str):
        # Validate path
        if not isinstance(path, str) or not path:
            raise ValueError("Path must be a non-empty string.")

        # Validate type during initialization
        if type not in ("shared", "exclusive"):
            raise ValueError("Type must strictly be 'shared' or 'exclusive'.")

        self._path = path
        self._type = type

        # Lists remain fully mutable
        self.holders = []
        self.waiters = []

    @property
    def path(self):
        """Read-only property to ensure path immutability."""
        return self._path

    @property
    def type(self):
        """Read-only property to ensure type immutability."""
        return self._type
