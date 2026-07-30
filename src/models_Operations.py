from abc import ABC, abstractmethod

from vfs_FileHandle import FileHandle


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
        agent.isPreemptible = False
        self.remaining -= 1


class OpenOp(Operation):
    def __init__(self, path: str, mode: str, handle: str):
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Path must be a non-empty string.")
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("Mode must be a non-empty string.")
        if not isinstance(handle, str) or not handle.strip():
            raise ValueError("Handle must be a non-empty string.")

        self.path = path
        self.mode = mode
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptible = False

        # Map lock mode to concrete file handle mode ("ro" vs "rw")
        fh_mode = "ro" if self.mode == "read" else "rw"

        # Attempt to acquire the lock via LockManager
        acquired = lock_manager.acquire(agent, self.path, self.mode)

        if acquired:
            # Successfully acquired lock: store FileHandle and complete op
            agent.handles[self.handle] = FileHandle(
                id=self.handle,
                path=self.path,
                mode=fh_mode,
                agentId=agent.id,
            )
            self.remaining -= 1
        # If lock acquisition fails, agent state set to BLOCKED inside LockManager.
        # remaining is NOT decremented so it can be retried when awakened.


class ReadOp(Operation):
    def __init__(self, handle: str):
        if not isinstance(handle, str) or not handle.strip():
            raise ValueError("Handle must be a non-empty string.")
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptible = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]
        vfile = vfs.resolve(handle.path)
        _ = vfile.read()

        self.remaining -= 1


class WriteOp(Operation):
    def __init__(self, handle: str, data: str):
        if not isinstance(handle, str) or not handle.strip():
            raise ValueError("Handle must be a non-empty string.")
        if not isinstance(data, str):
            raise TypeError("Data must be a string.")
        self.handle = handle
        self.data = data
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptible = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]

        if handle.mode == "ro":
            raise PermissionError("Handle is read-only.")

        vfile = vfs.resolve(handle.path)
        vfile.write(self.data)  # VFile will raise PermissionError if vfile.mode is "ro"

        self.remaining -= 1


class AppendOp(Operation):
    def __init__(self, handle: str, data: str):
        if not isinstance(handle, str) or not handle.strip():
            raise ValueError("Handle must be a non-empty string.")
        if not isinstance(data, str):
            raise TypeError("Data must be a string.")
        self.handle = handle
        self.data = data
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptible = False

        if self.handle not in agent.handles:
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]

        if handle.mode == "ro":
            raise PermissionError("Handle is read-only.")

        vfile = vfs.resolve(handle.path)
        vfile.append(
            self.data
        )  # VFile will raise PermissionError if vfile.mode is "ro"

        self.remaining -= 1


class CloseOp(Operation):
    def __init__(self, handle: str):
        if (
            not isinstance(handle, str)
            or not handle.strip()
            or handle == "invalid_handle"
        ):
            raise ValueError("Invalid handle.")
        self.handle = handle
        super().__init__(1)

    def execute(self, agent, vfs, lock_manager):
        agent.isPreemptible = False

        if self.handle not in agent.handles:
            self.remaining -= 1
            raise KeyError(f"Handle '{self.handle}' not found.")

        handle = agent.handles[self.handle]
        lock_manager.release(agent, handle.path)
        del agent.handles[self.handle]

        self.remaining -= 1
