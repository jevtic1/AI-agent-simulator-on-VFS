from abc import ABC, abstractmethod


class DummyFileHandle:
    """A lightweight representation of a FileHandle for OpenOp to instantiate unconditionally."""

    def __init__(self, path: str, mode: str):
        self.path = path
        self.mode = mode


class Operation(ABC):
    def __init__(self, remaining: int):
        self.remaining = remaining

    @abstractmethod
    def execute(self, agent, vfs, lock_manager):
        pass


class ThinkOp(Operation):
    def __init__(self, duration: int):
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError("Duration must be a positive integer.")
        self.duration = duration
        super().__init__(duration)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        # ThinkOp only simulates CPU computation time
        self.remaining -= 1


class OpenOp(Operation):
    def __init__(self, path: str, mode: str, handle: str):
        if not path or not mode or not handle:
            raise ValueError("Path, mode, and handle must be non-empty strings.")
        self.path = path
        self.mode = mode
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        # OpenOp unconditionally creates a FileHandle for now
        agent.handles[self.handle] = DummyFileHandle(self.path, self.mode)

        self.remaining -= 1


class ReadOp(Operation):
    def __init__(self, handle: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]
        vfile = vfs.resolve(handle.path)

        # Read the content (just accessing it for now)
        _ = vfile.content

        self.remaining -= 1


class WriteOp(Operation):
    def __init__(self, handle: str, data: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        self.data = data
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]

        if handle.mode == "r":
            raise PermissionError("File handle is not opened for writing.")

        vfile = vfs.resolve(handle.path)
        if vfile.mount.mode == "ro":
            raise PermissionError("Target mount is read-only.")

        # Overwrite content entirely
        vfile.content = self.data

        self.remaining -= 1


class AppendOp(Operation):
    def __init__(self, handle: str, data: str):
        if not handle:
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        self.data = data
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]

        if handle.mode == "r":
            raise PermissionError("File handle is not opened for appending.")

        vfile = vfs.resolve(handle.path)
        if vfile.mount.mode == "ro":
            raise PermissionError("Target mount is read-only.")

        # Append data to the content
        vfile.content += self.data

        self.remaining -= 1


class CloseOp(Operation):
    def __init__(self, handle: str):
        if not handle or handle == "invalid_handle":
            raise ValueError("Invalid handle.")
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptive = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]
        lock_manager.release(agent, handle.path)

        # Remove the handle from the agent's table
        del agent.handles[self.handle]

        self.remaining -= 1
