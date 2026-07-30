from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LockRequest:
    agentId: str
    mode: str
