import pytest
from src.vfs_VFS import VFS

from src.vfs_Mount import Mount
from src.vfs_VFile import VFile


@pytest.fixture
def physical_fs(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    (work_dir / "a.txt").write_text("content A")
    (work_dir / "b.txt").write_text("content B")
    (tmp_path / "shared.txt").write_text("shared content")

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    return tmp_path


@pytest.fixture
def vfs():
    return VFS()


@pytest.fixture
def populated_vfs(vfs, physical_fs):
    vfs.mount(source=str(physical_fs / "work"), target="/work", mode="rw")
    vfs.mount(source=str(physical_fs / "shared.txt"), target="/shared.txt", mode="ro")
    return vfs


class TestVFS:
    def test_initial_state(self, vfs):
        assert hasattr(vfs, "mounts")
        assert hasattr(vfs, "files")
        assert isinstance(vfs.mounts, list)
        assert isinstance(vfs.files, list)
        assert len(vfs.mounts) == 0
        assert len(vfs.files) == 0

    def test_mount_single_file_ro(self, vfs, physical_fs):
        src = str(physical_fs / "shared.txt")
        target = "/shared/shared.txt"

        vfs.mount(source=src, target=target, mode="ro")

        assert len(vfs.mounts) == 1
        assert isinstance(vfs.mounts[0], Mount)
        assert vfs.mounts[0].source == src
        assert vfs.mounts[0].target == target
        assert vfs.mounts[0].mode == "ro"

        assert len(vfs.files) == 1
        assert isinstance(vfs.files[0], VFile)
        assert vfs.files[0].path == target
        assert vfs.files[0].content == "shared content"
        assert vfs.files[0].mode == "ro"

    def test_mount_directory_rw(self, vfs, physical_fs):
        vfs.mount(source=str(physical_fs / "work"), target="/work", mode="rw")

        assert len(vfs.mounts) == 1
        assert len(vfs.files) == 2

        paths = [f.path for f in vfs.files]
        assert "/work/a.txt" in paths
        assert "/work/b.txt" in paths
        assert all(f.mode == "rw" for f in vfs.files)

    def test_mount_empty_directory(self, vfs, physical_fs):
        vfs.mount(source=str(physical_fs / "empty"), target="/empty", mode="ro")
        assert len(vfs.mounts) == 1
        assert len(vfs.files) == 0

    @pytest.mark.parametrize(
        "invalid_mode", ["read", "write", "r", "w", "RO", "", None]
    )
    def test_mount_invalid_mode(self, vfs, physical_fs, invalid_mode):
        src = str(physical_fs / "shared.txt")
        with pytest.raises(ValueError):
            vfs.mount(source=src, target="/shared.txt", mode=invalid_mode)

    def test_mount_nonexistent_source(self, vfs):
        with pytest.raises((FileNotFoundError, ValueError)):
            vfs.mount(source="/does/not/exist", target="/target", mode="ro")

    @pytest.mark.parametrize("invalid_target", ["relative/path", "path", "", None])
    def test_mount_invalid_target(self, vfs, physical_fs, invalid_target):
        src = str(physical_fs / "shared.txt")
        with pytest.raises(ValueError):
            vfs.mount(source=src, target=invalid_target, mode="ro")

    def test_resolve_existing_file(self, populated_vfs):
        vfile = populated_vfs.resolve("/work/a.txt")
        assert vfile is not None
        assert isinstance(vfile, VFile)
        assert vfile.path == "/work/a.txt"
        assert vfile.content == "content A"
        assert vfile.mode == "rw"

    def test_resolve_root_level_file(self, populated_vfs):
        vfile = populated_vfs.resolve("/shared.txt")
        assert vfile is not None
        assert vfile.path == "/shared.txt"
        assert vfile.mode == "ro"

    def test_resolve_non_existent(self, populated_vfs):
        with pytest.raises(FileNotFoundError):
            populated_vfs.resolve("/work/does_not_exist.txt")

    def test_resolve_invalid_path(self, populated_vfs):
        with pytest.raises((ValueError, FileNotFoundError)):
            populated_vfs.resolve("work/a.txt")

    def test_in_memory_isolation(self, vfs, physical_fs):
        src = physical_fs / "real.txt"
        src.write_text("original content")

        vfs.mount(source=str(src), target="/real.txt", mode="rw")
        vfile = vfs.resolve("/real.txt")

        try:
            vfile.content = "modified content"
        except Exception:
            idx = vfs.files.index(vfile)
            vfs.files[idx] = VFile(
                path=vfile.path, content="modified content", mode=vfile.mode
            )

        assert src.read_text() == "original content"
