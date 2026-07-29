from abc import ABC, abstractmethod


class Operation(ABC):
    @abstractmethod
    def execute(self, agent, vfs, lock_manager):
        pass


class ThinkOp(Operation):
    def __init__(self, duration: int):
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        self.duration = duration

    def execute(self, agent, vfs, lock_manager):
        # ThinkOp only simulates CPU computation time
        pass


class OpenOp(Operation):
    def __init__(self, path: str, mode: str, handle: str):
        if not path or not mode or not handle:
            raise ValueError("Path, mode, and handle must be non-empty strings.")
        self.path = path
        self.mode = mode
        self.handle = handle

    def execute(self, agent, vfs, lock_manager):
        if lock_manager.acquire(agent, self.path, self.mode):
            return vfs.resolve(self.path)
        return None


class ReadOp(Operation):
    def __init__(self, handle: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle

    def execute(self, agent, vfs, lock_manager):
        pass


class WriteOp(Operation):
    def __init__(self, handle: str, data: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        self.data = data

    def execute(self, agent, vfs, lock_manager):
        pass


class AppendOp(Operation):
    def __init__(self, handle: str, data: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        self.data = data

    def execute(self, agent, vfs, lock_manager):
        pass


class CloseOp(Operation):
    def __init__(self, handle: str):
        if not handle or handle == "invalid_handle":
            raise ValueError("Invalid handle.")
        self.handle = handle

    def execute(self, agent, vfs, lock_manager):
        lock_manager.release(agent, self.handle)
