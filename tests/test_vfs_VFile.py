import pytest

from src.vfs_VFile import VFile

PATH = "/work/a.txt"
RO = "ro"
RW = "rw"
VALIDATION_ERRORS = (ValueError, TypeError)


class TestVFileConstruction:
    def test_construction_and_defaults(self):
        f1 = VFile(path=PATH, content="hello", mode=RW)
        assert f1.path == PATH
        assert f1.content == "hello"
        assert f1.mode == RW

        f2 = VFile(path=PATH, mode=RO)
        assert f2.content == ""

    def test_positional_args(self):
        f = VFile(PATH, "hello", RW)
        assert (f.path, f.content, f.mode) == (PATH, "hello", RW)

    def test_instance_independence(self):
        f1 = VFile(path=PATH, content="a", mode=RW)
        f2 = VFile(path=PATH, content="a", mode=RW)
        f1.write("changed")
        assert f2.content == "a"


class TestVFileValidation:
    @pytest.mark.parametrize(
        "valid_path", ["/a.txt", "/work/a.txt", "/deeply/nested.md", "/"]
    )
    def test_absolute_paths_accepted(self, valid_path):
        assert VFile(path=valid_path, mode=RO).path == valid_path

    @pytest.mark.parametrize(
        "bad_path", ["a.txt", "relative/path.txt", "", " ", "./a", "../a"]
    )
    def test_invalid_paths_rejected(self, bad_path):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=bad_path, mode=RO)

    @pytest.mark.parametrize("invalid_type", [None, 123, "!5"])
    def test_invalid_path_types(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=invalid_type, mode=RO)

    @pytest.mark.parametrize("mode", [RO, RW])
    def test_valid_modes(self, mode):
        assert VFile(path=PATH, mode=mode).mode == mode

    @pytest.mark.parametrize(
        "bad_mode", ["read", "write", "RO", "RW", "r", "w", "", " ", "ro "]
    )
    def test_invalid_mode_strings(self, bad_mode):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=PATH, mode=bad_mode)

    @pytest.mark.parametrize("invalid_type", [None, 0])
    def test_invalid_mode_types(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=PATH, mode=invalid_type)

    @pytest.mark.parametrize("invalid_content", [123, None])
    def test_invalid_content_types(self, invalid_content):
        with pytest.raises(TypeError):
            VFile(path=PATH, content=invalid_content, mode=RW)

    def test_read_only_properties(self):
        f = VFile(path=PATH, mode=RO)
        with pytest.raises(AttributeError):
            f.path = "/other.txt"
        with pytest.raises(AttributeError):
            f.mode = RW


class TestVFileOperations:
    def test_read_behavior(self):
        f = VFile(path=PATH, content="hello", mode=RO)
        assert f.read() == "hello"
        assert f.read() == f.read()

        f_empty = VFile(path=PATH, mode=RO)
        assert f_empty.read() == ""

    def test_write_behavior(self):
        f = VFile(path=PATH, content="old", mode=RW)
        f.write("new")
        assert f.read() == "new"

        f.write("")
        assert f.content == ""

    def test_write_permissions_and_types(self):
        f = VFile(path=PATH, content="original", mode=RO)
        with pytest.raises(PermissionError):
            f.write("change")
        assert f.content == "original"

        f_rw = VFile(path=PATH, content="a", mode=RW)
        with pytest.raises(TypeError):
            f_rw.write(123)

    def test_append_behavior(self):
        f = VFile(path=PATH, content="A\n", mode=RW)
        f.append("B\n")
        assert f.content == "A\nB\n"

        f.append("")
        assert f.content == "A\nB\n"

    def test_append_permissions_and_types(self):
        f = VFile(path=PATH, content="original", mode=RO)
        with pytest.raises(PermissionError):
            f.append("change")
        assert f.content == "original"

        f_rw = VFile(path=PATH, content="a", mode=RW)
        with pytest.raises(TypeError):
            f_rw.append(123)

    def test_write_and_append_interactions(self):
        f = VFile(path=PATH, mode=RW)
        f.append("A1\n")
        f.write("reset")
        assert f.content == "reset"

        f.append("-suffix")
        assert f.content == "reset-suffix"


class TestVFileEdgeCases:
    def test_unicode_support(self):
        f = VFile(path=PATH, content="šarena 你好", mode=RW)
        assert f.read() == "šarena 你好"
        f.append("čćžšđ")
        assert f.content == "šarena 你好čćžšđ"

    def test_special_characters_and_whitespace(self):
        special = "quotes \" ' slashes \\ / tabs \t \n   "
        f = VFile(path=PATH, content=special, mode=RW)
        assert f.content == special

    def test_large_content_and_many_appends(self):
        big = "x" * 1_000_000
        f = VFile(path=PATH, content=big, mode=RW)
        f.append("y")
        assert len(f.content) == 1_000_001

        f2 = VFile(path=PATH, mode=RW)
        for i in range(1000):
            f2.append(str(i % 10))
        assert len(f2.content) == 1000

    def test_identity_equality(self):
        f1 = VFile(path=PATH, content="same", mode=RW)
        f2 = VFile(path=PATH, content="same", mode=RW)
        assert f1 is not f2

    def test_dunder_methods(self):
        f = VFile(path=PATH, content="anything", mode=RW)
        assert isinstance(repr(f), str)
        assert isinstance(str(f), str)
