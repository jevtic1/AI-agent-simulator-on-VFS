"""
Test suite for VFile.

ASSUMED API CONTRACT (implementation does not exist yet — TDD):

    from src.vfs import VFile

    class VFile:
        def __init__(self, path: str, content: str = "", mode: str = "ro"):
            ...

        @property
        def path(self) -> str: ...   # read-only after construction

        @property
        def mode(self) -> str: ...   # read-only after construction

        content: str                  # public, mutable buffer — the current
                                       # in-memory contents of the file

        def read(self) -> str:
            '''Return current content. Allowed in both "ro" and "rw" mode.'''

        def write(self, data: str) -> None:
            '''Replace content entirely. Raises PermissionError if mode == "ro".'''

        def append(self, data: str) -> None:
            '''Append data to content. Raises PermissionError if mode == "ro".'''

Assumed validation rules (constructor raises on violation):
    - path: non-empty string starting with "/" (absolute VFS path, same rule
      as Mount.target) -> ValueError if malformed, TypeError if not a string
    - mode: exactly "ro" or "rw" -> ValueError if invalid, TypeError if not a string
    - content: must be a string if provided -> TypeError otherwise; defaults to ""

Assumed behavior of write()/append():
    - Both require `data` to be a string -> TypeError otherwise
    - Both raise PermissionError (not ValueError) when mode == "ro", since this
      is an access-control failure, not a malformed-input failure
    - write() fully replaces content (not a partial/merge operation)
    - append() concatenates data onto the end of the existing content
    - Neither mutates content when they raise (failed operations are no-ops)

Assumed structural properties:
    - path and mode are immutable after construction (read-only properties)
    - content is a freely mutable attribute; read()/write()/append() are the
      sanctioned way to interact with it and are what enforce `mode`, but the
      attribute itself is not access-protected (simulation/report code is
      expected to read `.content` directly for the final VFS-state printout)
    - VFile does not define custom equality/hashing — two instances are only
      equal to themselves (default identity semantics), since a VFile
      represents a distinct, stateful entity, not a value type like Mount

If the actual implementation differs (e.g. raises ValueError instead of
PermissionError, or exposes content only via read()), adjust the invocations
below — the test *cases* are the source of truth, not the exact mechanism.
"""

import pytest

from src.vfs_VFile import VFile

# --- Shared constants ----------------------------------------------------

VALID_PATH = "/work/a.txt"
RO_MODE = "ro"
RW_MODE = "rw"

VALIDATION_ERRORS = (ValueError, TypeError)


# =============================================================================
# 1. Construction
# =============================================================================


class TestConstruction:
    def test_construct_with_explicit_content(self):
        f = VFile(path=VALID_PATH, content="hello", mode=RW_MODE)
        assert f.path == VALID_PATH
        assert f.content == "hello"
        assert f.mode == RW_MODE

    def test_construct_defaults_content_to_empty_string(self):
        f = VFile(path=VALID_PATH, mode=RO_MODE)
        assert f.content == ""

    def test_construct_with_ro_mode(self):
        f = VFile(path=VALID_PATH, content="x", mode=RO_MODE)
        assert f.mode == RO_MODE

    def test_construct_with_rw_mode(self):
        f = VFile(path=VALID_PATH, content="x", mode=RW_MODE)
        assert f.mode == RW_MODE

    def test_construct_with_positional_args(self):
        f = VFile(VALID_PATH, "hello", RW_MODE)
        assert (f.path, f.content, f.mode) == (VALID_PATH, "hello", RW_MODE)

    def test_construct_with_empty_string_content_explicitly(self):
        f = VFile(path=VALID_PATH, content="", mode=RW_MODE)
        assert f.content == ""

    def test_two_separately_constructed_files_are_independent(self):
        f1 = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        f2 = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        f1.write("changed")
        assert f2.content == "a"


# =============================================================================
# 2. Path validation
# =============================================================================


class TestPathValidation:
    @pytest.mark.parametrize(
        "valid_path",
        [
            "/a.txt",
            "/work/a.txt",
            "/deeply/nested/path/file.md",
            "/",
        ],
    )
    def test_accepts_absolute_paths(self, valid_path):
        f = VFile(path=valid_path, mode=RO_MODE)
        assert f.path == valid_path

    @pytest.mark.parametrize(
        "bad_path",
        [
            "a.txt",
            "relative/path.txt",
            "",
            " ",
            "./a.txt",
            "../a.txt",
        ],
    )
    def test_rejects_non_absolute_or_empty_path(self, bad_path):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=bad_path, mode=RO_MODE)

    def test_rejects_none_path(self):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=None, mode=RO_MODE)

    def test_rejects_non_string_path(self):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=123, mode=RO_MODE)

    def test_path_is_read_only(self):
        f = VFile(path=VALID_PATH, mode=RO_MODE)
        with pytest.raises(AttributeError):
            f.path = "/other.txt"


# =============================================================================
# 3. Mode validation
# =============================================================================


class TestModeValidation:
    @pytest.mark.parametrize("mode", ["ro", "rw"])
    def test_accepts_only_documented_modes(self, mode):
        f = VFile(path=VALID_PATH, mode=mode)
        assert f.mode == mode

    @pytest.mark.parametrize(
        "bad_mode",
        [
            "read",
            "write",
            "RO",
            "RW",
            "r",
            "w",
            "",
            " ",
            "ro ",
        ],
    )
    def test_rejects_invalid_mode_strings(self, bad_mode):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=VALID_PATH, mode=bad_mode)

    def test_rejects_none_mode(self):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=VALID_PATH, mode=None)

    def test_rejects_non_string_mode(self):
        with pytest.raises(VALIDATION_ERRORS):
            VFile(path=VALID_PATH, mode=0)

    def test_mode_is_read_only(self):
        f = VFile(path=VALID_PATH, mode=RO_MODE)
        with pytest.raises(AttributeError):
            f.mode = "rw"


# =============================================================================
# 4. Content type validation (constructor)
# =============================================================================


class TestContentTypeValidation:
    def test_rejects_non_string_content(self):
        with pytest.raises(TypeError):
            VFile(path=VALID_PATH, content=123, mode=RW_MODE)

    def test_rejects_none_content(self):
        with pytest.raises(TypeError):
            VFile(path=VALID_PATH, content=None, mode=RW_MODE)

    def test_accepts_whitespace_only_content(self):
        # unlike Mount.source, file *content* has no "must be meaningful" rule —
        # a file full of whitespace is a perfectly valid file
        f = VFile(path=VALID_PATH, content="   \n\t  ", mode=RW_MODE)
        assert f.content == "   \n\t  "


# =============================================================================
# 5. read()
# =============================================================================


class TestRead:
    def test_read_returns_initial_content(self):
        f = VFile(path=VALID_PATH, content="hello", mode=RO_MODE)
        assert f.read() == "hello"

    def test_read_allowed_on_ro_file(self):
        f = VFile(path=VALID_PATH, content="hello", mode=RO_MODE)
        assert f.read() == "hello"  # should not raise

    def test_read_allowed_on_rw_file(self):
        f = VFile(path=VALID_PATH, content="hello", mode=RW_MODE)
        assert f.read() == "hello"

    def test_read_is_idempotent(self):
        f = VFile(path=VALID_PATH, content="hello", mode=RO_MODE)
        assert f.read() == f.read() == "hello"

    def test_read_reflects_content_after_write(self):
        f = VFile(path=VALID_PATH, content="old", mode=RW_MODE)
        f.write("new")
        assert f.read() == "new"

    def test_read_on_empty_file_returns_empty_string(self):
        f = VFile(path=VALID_PATH, mode=RO_MODE)
        assert f.read() == ""


# =============================================================================
# 6. write()
# =============================================================================


class TestWrite:
    def test_write_replaces_content_on_rw_file(self):
        f = VFile(path=VALID_PATH, content="old", mode=RW_MODE)
        f.write("new")
        assert f.content == "new"

    def test_write_fully_replaces_not_merges(self):
        f = VFile(path=VALID_PATH, content="a long original string", mode=RW_MODE)
        f.write("x")
        assert f.content == "x"

    def test_write_empty_string_clears_content(self):
        f = VFile(path=VALID_PATH, content="something", mode=RW_MODE)
        f.write("")
        assert f.content == ""

    def test_write_twice_reflects_latest_value(self):
        f = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        f.write("b")
        f.write("c")
        assert f.content == "c"

    def test_write_raises_permission_error_on_ro_file(self):
        f = VFile(path=VALID_PATH, content="original", mode=RO_MODE)
        with pytest.raises(PermissionError):
            f.write("attempted change")

    def test_write_on_ro_file_does_not_mutate_content(self):
        f = VFile(path=VALID_PATH, content="original", mode=RO_MODE)
        with pytest.raises(PermissionError):
            f.write("attempted change")
        assert f.content == "original"

    def test_write_rejects_non_string_data(self):
        f = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        with pytest.raises(TypeError):
            f.write(123)

    def test_write_rejects_none_data(self):
        f = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        with pytest.raises(TypeError):
            f.write(None)


# =============================================================================
# 7. append()
# =============================================================================


class TestAppend:
    def test_append_concatenates_onto_existing_content(self):
        f = VFile(path=VALID_PATH, content="agent A\n", mode=RW_MODE)
        f.append("agent B\n")
        assert f.content == "agent A\nagent B\n"

    def test_append_on_empty_file(self):
        f = VFile(path=VALID_PATH, mode=RW_MODE)
        f.append("first line")
        assert f.content == "first line"

    def test_multiple_appends_accumulate_in_call_order(self):
        f = VFile(path=VALID_PATH, mode=RW_MODE)
        f.append("A1\n")
        f.append("A2\n")
        f.append("A3\n")
        assert f.content == "A1\nA2\nA3\n"

    def test_append_empty_string_is_a_no_op(self):
        f = VFile(path=VALID_PATH, content="unchanged", mode=RW_MODE)
        f.append("")
        assert f.content == "unchanged"

    def test_append_raises_permission_error_on_ro_file(self):
        f = VFile(path=VALID_PATH, content="original", mode=RO_MODE)
        with pytest.raises(PermissionError):
            f.append("attempted change")

    def test_append_on_ro_file_does_not_mutate_content(self):
        f = VFile(path=VALID_PATH, content="original", mode=RO_MODE)
        with pytest.raises(PermissionError):
            f.append("attempted change")
        assert f.content == "original"

    def test_append_rejects_non_string_data(self):
        f = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        with pytest.raises(TypeError):
            f.append(123)

    def test_append_rejects_none_data(self):
        f = VFile(path=VALID_PATH, content="a", mode=RW_MODE)
        with pytest.raises(TypeError):
            f.append(None)

    def test_write_after_append_replaces_everything(self):
        f = VFile(path=VALID_PATH, mode=RW_MODE)
        f.append("A1\n")
        f.append("A2\n")
        f.write("reset")
        assert f.content == "reset"

    def test_append_after_write_builds_on_new_base(self):
        f = VFile(path=VALID_PATH, content="original", mode=RW_MODE)
        f.write("base")
        f.append("-suffix")
        assert f.content == "base-suffix"


# =============================================================================
# 8. Edge cases
# =============================================================================


class TestEdgeCases:
    def test_unicode_content_round_trip(self):
        f = VFile(
            path=VALID_PATH, content="šarena tekstualna datoteka 你好", mode=RW_MODE
        )
        assert f.read() == "šarena tekstualna datoteka 你好"

    def test_unicode_append(self):
        f = VFile(path=VALID_PATH, content="pozdrav: ", mode=RW_MODE)
        f.append("čćžšđ")
        assert f.content == "pozdrav: čćžšđ"

    def test_content_preserves_newlines_exactly(self):
        f = VFile(path=VALID_PATH, content="line1\nline2\nline3", mode=RW_MODE)
        assert f.content.count("\n") == 2
        assert f.content == "line1\nline2\nline3"

    def test_content_preserves_special_characters(self):
        special = "quotes \" ' and slashes \\ / and tabs \t"
        f = VFile(path=VALID_PATH, content=special, mode=RW_MODE)
        assert f.content == special

    def test_very_large_content(self):
        big = "x" * 1_000_000
        f = VFile(path=VALID_PATH, content=big, mode=RW_MODE)
        assert len(f.content) == 1_000_000
        f.append("y")
        assert len(f.content) == 1_000_001

    def test_many_small_appends(self):
        f = VFile(path=VALID_PATH, mode=RW_MODE)
        for i in range(1000):
            f.append(str(i % 10))
        assert len(f.content) == 1000

    def test_write_same_value_twice_is_stable(self):
        f = VFile(path=VALID_PATH, content="stable", mode=RW_MODE)
        f.write("stable")
        f.write("stable")
        assert f.content == "stable"

    def test_root_path_file(self):
        f = VFile(path="/", content="root content", mode=RW_MODE)
        assert f.path == "/"

    def test_two_instances_with_identical_fields_are_not_equal(self):
        # VFile is a stateful entity, not a value object — no __eq__ override assumed
        f1 = VFile(path=VALID_PATH, content="same", mode=RW_MODE)
        f2 = VFile(path=VALID_PATH, content="same", mode=RW_MODE)
        assert f1 is not f2

    def test_str_or_repr_does_not_raise(self):
        f = VFile(path=VALID_PATH, content="anything", mode=RW_MODE)
        assert isinstance(repr(f), str)
        assert isinstance(str(f), str)
