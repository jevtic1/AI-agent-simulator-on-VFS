from dataclasses import dataclass


@dataclass(frozen=True)
class FileHandle:
    id: str
    path: str
    mode: str
    agentId: str

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must be a non-empty string.")

        if not isinstance(self.path, str) or not self.path.startswith("/"):
            raise ValueError("path must be a string starting with '/'.")

        if self.mode not in ("ro", "rw"):
            raise ValueError("mode must be exactly 'ro' or 'rw'.")

        if not isinstance(self.agentId, str) or not self.agentId.strip():
            raise ValueError("agentId must be a non-empty string.")
