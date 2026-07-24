"""
Test suite for Mount.

ASSUMED API CONTRACT (implementation does not exist yet — TDD):

    from src.vfs import Mount

    @dataclass(frozen=True)
    class Mount:
        source: str    # real file/directory path being mounted (per assignment: can be
                        # relative or absolute, e.g. "input/shared")
        target: str    # absolute path in the VFS namespace (per assignment spec:
                        # "target: apsolutna putanja u VFS-u" -> MUST start with "/")
        mode: str       # exactly "ro" or "rw" (per assignment spec)

Assumed validation rules (constructor raises ValueError on violation):
    - mode must be exactly "ro" or "rw" (case-sensitive, no aliases like "read"/"write")
    - target must be a non-empty string starting with "/"
    - source must be a non-empty, non-whitespace-only string
    - None is never an acceptable value for any field
    - non-string types for any field raise TypeError (or ValueError — either is
      acceptable per constructor design; tests accept both, see note below)

Assumed structural properties:
    - Mount is immutable (frozen) — field reassignment after construction raises
    - Two Mounts with identical (source, target, mode) are equal and share a hash
    - Mount is hashable (usable in sets / as dict keys)

If the actual implementation differs (e.g. validates via a separate `validate()`
method instead of raising in __init__, or uses TypeError vs ValueError), adjust
the invocations below — the test *cases* are the source of truth, not the exact
mechanism.
"""

from dataclasses import FrozenInstanceError

import pytest
from src.vfs_Mount import Mount

# --- Shared constants ---------------------------------------------------------

VALID_SOURCE = "input/shared"
VALID_TARGET = "/shared"
VALID_MODE_RO = "ro"
VALID_MODE_RW = "rw"

# Errors that indicate "rejected input" — implementation may reasonably choose
# either, so validation tests accept both unless a spec-grounded rule says otherwise.
VALIDATION_ERRORS = (ValueError, TypeError)


# =============================================================================
# 1. Standard construction
# =============================================================================


class TestConstruction:
    def test_construct_with_ro_mode(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m.source == VALID_SOURCE
        assert m.target == VALID_TARGET
        assert m.mode == VALID_MODE_RO

    def test_construct_with_rw_mode(self):
        m = Mount(source="input/work", target="/work", mode=VALID_MODE_RW)
        assert m.mode == VALID_MODE_RW

    def test_construct_with_positional_args(self):
        m = Mount(VALID_SOURCE, VALID_TARGET, VALID_MODE_RO)
        assert (m.source, m.target, m.mode) == (
            VALID_SOURCE,
            VALID_TARGET,
            VALID_MODE_RO,
        )

    def test_construct_with_nested_target_path(self):
        m = Mount(source=VALID_SOURCE, target="/data/nested/dir", mode=VALID_MODE_RO)
        assert m.target == "/data/nested/dir"

    def test_construct_with_root_target(self):
        m = Mount(source=VALID_SOURCE, target="/", mode=VALID_MODE_RO)
        assert m.target == "/"

    def test_construct_with_relative_source_path(self):
        m = Mount(source="input/shared", target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m.source == "input/shared"

    def test_construct_with_absolute_source_path(self):
        m = Mount(source="/home/user/data", target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m.source == "/home/user/data"


# =============================================================================
# 2. Mode validation
# =============================================================================


class TestModeValidation:
    @pytest.mark.parametrize("mode", ["ro", "rw"])
    def test_accepts_only_documented_modes(self, mode):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=mode)
        assert m.mode == mode

    @pytest.mark.parametrize(
        "bad_mode",
        [
            "read",
            "write",
            "readonly",
            "readwrite",
            "RO",
            "RW",
            "Ro",
            "rW",
            "r",
            "w",
            "rwx",
            "",
            " ",
            "ro ",
            " rw",
        ],
    )
    def test_rejects_invalid_mode_strings(self, bad_mode):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=bad_mode)

    def test_rejects_none_mode(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=None)

    def test_rejects_non_string_mode(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=0)


# =============================================================================
# 3. Target path validation
# =============================================================================


class TestTargetValidation:
    @pytest.mark.parametrize(
        "valid_target",
        [
            "/",
            "/shared",
            "/work",
            "/a/b/c",
            "/deeply/nested/virtual/path",
        ],
    )
    def test_accepts_absolute_targets(self, valid_target):
        m = Mount(source=VALID_SOURCE, target=valid_target, mode=VALID_MODE_RO)
        assert m.target == valid_target

    @pytest.mark.parametrize(
        "bad_target",
        [
            "shared",  # missing leading slash
            "relative/path",  # relative path
            "",  # empty string
            " ",  # whitespace only
            "./shared",  # relative with dot
            "../shared",  # relative with parent-dir traversal
        ],
    )
    def test_rejects_non_absolute_or_empty_targets(self, bad_target):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=bad_target, mode=VALID_MODE_RO)

    def test_rejects_none_target(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=None, mode=VALID_MODE_RO)

    def test_rejects_non_string_target(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=VALID_SOURCE, target=123, mode=VALID_MODE_RO)


# =============================================================================
# 4. Source validation
# =============================================================================


class TestSourceValidation:
    def test_rejects_empty_source(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source="", target=VALID_TARGET, mode=VALID_MODE_RO)

    def test_rejects_whitespace_only_source(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source="   ", target=VALID_TARGET, mode=VALID_MODE_RO)

    def test_rejects_none_source(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=None, target=VALID_TARGET, mode=VALID_MODE_RO)

    def test_rejects_non_string_source(self):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=42, target=VALID_TARGET, mode=VALID_MODE_RO)


# =============================================================================
# 5. Equality and hashing
# =============================================================================


class TestEqualityAndHashing:
    def test_two_mounts_with_identical_fields_are_equal(self):
        m1 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        m2 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m1 == m2

    def test_mounts_differing_only_by_source_are_not_equal(self):
        m1 = Mount(source="input/shared", target=VALID_TARGET, mode=VALID_MODE_RO)
        m2 = Mount(source="input/other", target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m1 != m2

    def test_mounts_differing_only_by_target_are_not_equal(self):
        m1 = Mount(source=VALID_SOURCE, target="/shared", mode=VALID_MODE_RO)
        m2 = Mount(source=VALID_SOURCE, target="/other", mode=VALID_MODE_RO)
        assert m1 != m2

    def test_mounts_differing_only_by_mode_are_not_equal(self):
        m1 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode="ro")
        m2 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode="rw")
        assert m1 != m2

    def test_mount_is_not_equal_to_unrelated_type(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        assert m != VALID_SOURCE
        assert m != {
            "source": VALID_SOURCE,
            "target": VALID_TARGET,
            "mode": VALID_MODE_RO,
        }
        assert m != None  # noqa: E711

    def test_equal_mounts_have_equal_hashes(self):
        m1 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        m2 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        assert hash(m1) == hash(m2)

    def test_mount_usable_in_a_set(self):
        m1 = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        m2 = Mount(
            source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO
        )  # duplicate
        m3 = Mount(source="input/work", target="/work", mode=VALID_MODE_RW)
        mount_set = {m1, m2, m3}
        assert len(mount_set) == 2


# =============================================================================
# 6. Immutability
# =============================================================================


class TestImmutability:
    def test_cannot_reassign_source_after_construction(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.source = "input/other"

    def test_cannot_reassign_target_after_construction(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.target = "/other"

    def test_cannot_reassign_mode_after_construction(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.mode = "rw"

    def test_cannot_add_new_attribute(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.extra_field = "not allowed"


# =============================================================================
# 7. String representation
# =============================================================================


class TestStringRepresentation:
    def test_repr_contains_all_field_values(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        r = repr(m)
        assert VALID_SOURCE in r
        assert VALID_TARGET in r
        assert VALID_MODE_RO in r

    def test_str_does_not_raise(self):
        m = Mount(source=VALID_SOURCE, target=VALID_TARGET, mode=VALID_MODE_RO)
        assert isinstance(str(m), str)
        assert len(str(m)) > 0


# =============================================================================
# 8. Edge cases
# =============================================================================


class TestEdgeCases:
    def test_target_with_trailing_slash_is_accepted_as_is(self):
        # Mount itself only validates format, it does not normalize —
        # normalization (if any) is VFS.mount()'s responsibility, not Mount's.
        m = Mount(source=VALID_SOURCE, target="/shared/", mode=VALID_MODE_RO)
        assert m.target == "/shared/"

    def test_source_with_special_characters(self):
        m = Mount(
            source="input/my folder (v2)", target=VALID_TARGET, mode=VALID_MODE_RO
        )
        assert m.source == "input/my folder (v2)"

    def test_source_with_unicode_characters(self):
        m = Mount(
            source="input/šarena_datoteka", target=VALID_TARGET, mode=VALID_MODE_RO
        )
        assert m.source == "input/šarena_datoteka"

    def test_target_with_unicode_characters(self):
        m = Mount(source=VALID_SOURCE, target="/podaci/šared", mode=VALID_MODE_RO)
        assert m.target == "/podaci/šared"

    def test_very_long_target_path(self):
        long_target = "/" + "/".join(f"dir{i}" for i in range(200))
        m = Mount(source=VALID_SOURCE, target=long_target, mode=VALID_MODE_RO)
        assert m.target == long_target

    def test_source_equal_to_target_string_is_allowed(self):
        # nothing in the spec forbids source and target looking similar,
        # e.g. mounting "/shared" (abs real path) onto VFS target "/shared"
        m = Mount(source="/shared", target="/shared", mode=VALID_MODE_RO)
        assert m.source == "/shared"
        assert m.target == "/shared"

    def test_two_mounts_can_share_the_same_source_with_different_modes(self):
        # e.g. mounting the same real directory twice, once ro once rw
        # at different virtual targets — Mount itself shouldn't forbid this,
        # any such policy belongs to VFS, not the data class
        m1 = Mount(source=VALID_SOURCE, target="/a", mode=VALID_MODE_RO)
        m2 = Mount(source=VALID_SOURCE, target="/b", mode=VALID_MODE_RW)
        assert m1.source == m2.source
        assert m1 != m2

    def test_target_that_is_only_a_slash_is_not_treated_as_empty(self):
        m = Mount(source=VALID_SOURCE, target="/", mode=VALID_MODE_RO)
        assert m.target == "/"
        assert m.target != ""
