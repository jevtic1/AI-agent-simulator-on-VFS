from dataclasses import FrozenInstanceError
import pytest
from src.vfs_Mount import Mount

SOURCE = "input/shared"
TARGET = "/shared"
RO = "ro"
RW = "rw"
VALIDATION_ERRORS = (ValueError, TypeError)


class TestMountConstruction:
    def test_valid_instantiation(self):
        m1 = Mount(source=SOURCE, target=TARGET, mode=RO)
        assert (m1.source, m1.target, m1.mode) == (SOURCE, TARGET, RO)

        m2 = Mount(source="input/work", target="/work", mode=RW)
        assert m2.mode == RW

    def test_positional_arguments(self):
        m = Mount(SOURCE, TARGET, RO)
        assert (m.source, m.target, m.mode) == (SOURCE, TARGET, RO)

    @pytest.mark.parametrize("target", ["/", "/data/nested/dir", "/shared"])
    def test_target_variations(self, target):
        m = Mount(source=SOURCE, target=target, mode=RO)
        assert m.target == target

    @pytest.mark.parametrize("source", ["input/shared", "/home/user/data"])
    def test_source_variations(self, source):
        m = Mount(source=source, target=TARGET, mode=RO)
        assert m.source == source


class TestMountValidation:
    @pytest.mark.parametrize("mode", [RO, RW])
    def test_valid_modes(self, mode):
        assert Mount(source=SOURCE, target=TARGET, mode=mode).mode == mode

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
    def test_invalid_mode_strings(self, bad_mode):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=SOURCE, target=TARGET, mode=bad_mode)

    @pytest.mark.parametrize("invalid_type", [None, 0])
    def test_invalid_mode_types(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=SOURCE, target=TARGET, mode=invalid_type)

    @pytest.mark.parametrize(
        "valid_target",
        ["/", "/shared", "/work", "/a/b/c", "/deeply/nested/virtual/path"],
    )
    def test_valid_targets(self, valid_target):
        assert Mount(source=SOURCE, target=valid_target, mode=RO).target == valid_target

    @pytest.mark.parametrize(
        "bad_target", ["shared", "relative/path", "", " ", "./shared", "../shared"]
    )
    def test_invalid_target_strings(self, bad_target):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=SOURCE, target=bad_target, mode=RO)

    @pytest.mark.parametrize("invalid_type", [None, 123])
    def test_invalid_target_types(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=SOURCE, target=invalid_type, mode=RO)

    @pytest.mark.parametrize("bad_source", ["", "   "])
    def test_invalid_source_strings(self, bad_source):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=bad_source, target=TARGET, mode=RO)

    @pytest.mark.parametrize("invalid_type", [None, 42])
    def test_invalid_source_types(self, invalid_type):
        with pytest.raises(VALIDATION_ERRORS):
            Mount(source=invalid_type, target=TARGET, mode=RO)


class TestMountEqualityAndHashing:
    def test_equality(self):
        m1 = Mount(source=SOURCE, target=TARGET, mode=RO)
        m2 = Mount(source=SOURCE, target=TARGET, mode=RO)
        assert m1 == m2

    def test_inequality(self):
        base = Mount(source=SOURCE, target=TARGET, mode=RO)
        assert base != Mount(source="input/other", target=TARGET, mode=RO)
        assert base != Mount(source=SOURCE, target="/other", mode=RO)
        assert base != Mount(source=SOURCE, target=TARGET, mode=RW)
        assert base != SOURCE
        assert base != {"source": SOURCE, "target": TARGET, "mode": RO}
        assert base is not None

    def test_hash_and_set_usability(self):
        m1 = Mount(source=SOURCE, target=TARGET, mode=RO)
        m2 = Mount(source=SOURCE, target=TARGET, mode=RO)
        m3 = Mount(source="input/work", target="/work", mode=RW)

        assert hash(m1) == hash(m2)
        assert len({m1, m2, m3}) == 2


class TestMountImmutability:
    def test_field_reassignment_raises(self):
        m = Mount(source=SOURCE, target=TARGET, mode=RO)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.source = "input/other"
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.target = "/other"
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.mode = RW
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.extra_field = "not allowed"


class TestMountEdgeCases:
    def test_repr_and_str(self):
        m = Mount(source=SOURCE, target=TARGET, mode=RO)
        r = repr(m)
        assert SOURCE in r and TARGET in r and RO in r
        assert isinstance(str(m), str) and len(str(m)) > 0

    def test_trailing_slash_target(self):
        m = Mount(source=SOURCE, target="/shared/", mode=RO)
        assert m.target == "/shared/"

    def test_special_and_unicode_characters(self):
        m1 = Mount(source="input/my folder (v2)", target=TARGET, mode=RO)
        assert m1.source == "input/my folder (v2)"

        m2 = Mount(source="input/šarena_datoteka", target="/podaci/šared", mode=RO)
        assert m2.source == "input/šarena_datoteka"
        assert m2.target == "/podaci/šared"

    def test_very_long_target_path(self):
        long_target = "/" + "/".join(f"dir{i}" for i in range(200))
        m = Mount(source=SOURCE, target=long_target, mode=RO)
        assert m.target == long_target

    def test_identical_source_and_target_strings(self):
        m = Mount(source="/shared", target="/shared", mode=RO)
        assert m.source == "/shared"
        assert m.target == "/shared"

    def test_shared_source_different_targets_and_modes(self):
        m1 = Mount(source=SOURCE, target="/a", mode=RO)
        m2 = Mount(source=SOURCE, target="/b", mode=RW)
        assert m1.source == m2.source
        assert m1 != m2

    def test_root_target_handling(self):
        m = Mount(source=SOURCE, target="/", mode=RO)
        assert m.target == "/"
        assert m.target != ""
