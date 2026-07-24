class VFile:
    def __init__(self, path: str, content: str = "", mode: str = "ro"):
        if not isinstance(path, str):
            raise TypeError("path must be a string")
        if not path.startswith("/"):
            raise ValueError("path must be an absolute path starting with '/'")

        if not isinstance(mode, str):
            raise TypeError("mode must be a string")
        if mode not in ("ro", "rw"):
            raise ValueError("mode must be 'ro' or 'rw'")

        if not isinstance(content, str):
            raise TypeError("content must be a string")

        self._path = path
        self._mode = mode
        self.content = content

    @property
    def path(self) -> str:
        return self._path

    @property
    def mode(self) -> str:
        return self._mode

    def read(self) -> str:
        return self.content

    def write(self, data: str) -> None:
        if not isinstance(data, str):
            raise TypeError("data must be a string")
        if self._mode != "rw":
            raise PermissionError(f"cannot write to read-only file {self._path}")
        self.content = data

    def append(self, data: str) -> None:
        if not isinstance(data, str):
            raise TypeError("data must be a string")
        if self._mode != "rw":
            raise PermissionError(f"cannot append to read-only file {self._path}")
        self.content += data
