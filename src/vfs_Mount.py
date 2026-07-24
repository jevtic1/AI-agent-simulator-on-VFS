from dataclasses import dataclass


@dataclass(frozen=True)
class Mount:
    source: str
    target: str
    mode: str

    def __post_init__(self):
        if not isinstance(self.source, str):
            raise TypeError("source must be a string")
        if not self.source.strip():
            raise ValueError("source must not be empty")

        if not isinstance(self.target, str):
            raise TypeError("target must be a string")
        if not self.target.startswith("/"):
            raise ValueError("target must be an absolute path starting with '/'")

        if not isinstance(self.mode, str):
            raise TypeError("mode must be a string")
        if self.mode not in ("ro", "rw"):
            raise ValueError("mode must be 'ro' or 'rw'")
