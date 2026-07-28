from pathlib import Path

from src.vfs_Mount import Mount
from src.vfs_VFile import VFile


class VFS:
    def __init__(self):
        self.mounts = []
        self.files = []

    def mount(self, source: str, target: str, mode: str):
        if mode not in ("ro", "rw"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'ro' or 'rw'.")

        if not target or not target.startswith("/"):
            raise ValueError("Target path must be an absolute path starting with '/'.")

        src_path = Path(source)

        if not src_path.exists():
            raise FileNotFoundError(f"Source path '{source}' does not exist.")

        self.mounts.append(Mount(source=source, target=target, mode=mode))

        if src_path.is_file():
            content = src_path.read_text()
            self.files.append(VFile(path=target, content=content, mode=mode))

        elif src_path.is_dir():
            target_base = target.rstrip("/")
            for item in src_path.iterdir():
                if item.is_file():
                    content = item.read_text()
                    item_target = f"{target_base}/{item.name}"
                    self.files.append(
                        VFile(path=item_target, content=content, mode=mode)
                    )

    def resolve(self, path: str):
        if not path or not path.startswith("/"):
            raise ValueError("Path must be an absolute path starting with '/'.")

        for vfile in self.files:
            if vfile.path == path:
                return vfile

        raise FileNotFoundError(f"File '{path}' not found in virtual file system.")
