from dataclasses import FrozenInstanceError

import pytest
from src.vfs_FileHandle import FileHandle

ID = "h_100"
PATH = "/mnt/data/report.txt"
RO = "ro"
RW = "rw"
AGENT_ID = "agent_1"
VALIDATION_ERRORS = (ValueError, TypeError)


class TestFileHandleConstruction:
    def test_valid_instantiation(self):
        handle = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        assert handle.id == ID
        assert handle.path == PATH
        assert handle.mode == RO
        assert handle.agentId == AGENT_ID

    def test_positional_arguments(self):
        handle = FileHandle(ID, PATH, RW, AGENT_ID)
        assert (handle.id, handle.path, handle.mode, handle.agentId) == (
            ID,
            PATH,
            RW,
            AGENT_ID,
        )


class TestFileHandleValidation:
    @pytest.mark.parametrize("invalid_id", ["", "   ", None, 123])
    def test_invalid_id_rejected(self, invalid_id):
        with pytest.raises(VALIDATION_ERRORS):
            FileHandle(id=invalid_id, path=PATH, mode=RO, agentId=AGENT_ID)

    @pytest.mark.parametrize(
        "valid_path", ["/", "/file.txt", "/deeply/nested/file.log"]
    )
    def test_valid_paths_accepted(self, valid_path):
        handle = FileHandle(id=ID, path=valid_path, mode=RO, agentId=AGENT_ID)
        assert handle.path == valid_path

    @pytest.mark.parametrize(
        "invalid_path", ["relative/file.txt", "", "   ", None, 404]
    )
    def test_invalid_path_rejected(self, invalid_path):
        with pytest.raises(VALIDATION_ERRORS):
            FileHandle(id=ID, path=invalid_path, mode=RO, agentId=AGENT_ID)

    @pytest.mark.parametrize("mode", [RO, RW])
    def test_valid_modes_accepted(self, mode):
        handle = FileHandle(id=ID, path=PATH, mode=mode, agentId=AGENT_ID)
        assert handle.mode == mode

    @pytest.mark.parametrize("invalid_mode", ["r", "w", "read", "RO", "", None, 1])
    def test_invalid_mode_rejected(self, invalid_mode):
        with pytest.raises(VALIDATION_ERRORS):
            FileHandle(id=ID, path=PATH, mode=invalid_mode, agentId=AGENT_ID)

    @pytest.mark.parametrize("invalid_agent_id", ["", "   ", None, 999])
    def test_invalid_agent_id_rejected(self, invalid_agent_id):
        with pytest.raises(VALIDATION_ERRORS):
            FileHandle(id=ID, path=PATH, mode=RO, agentId=invalid_agent_id)


class TestFileHandleImmutability:
    def test_fields_are_read_only(self):
        handle = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)

        with pytest.raises((FrozenInstanceError, AttributeError)):
            handle.id = "h_101"

        with pytest.raises((FrozenInstanceError, AttributeError)):
            handle.path = "/new/path.txt"

        with pytest.raises((FrozenInstanceError, AttributeError)):
            handle.mode = RW

        with pytest.raises((FrozenInstanceError, AttributeError)):
            handle.agentId = "agent_2"


class TestFileHandleEqualityAndHashing:
    def test_equality(self):
        h1 = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        h2 = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        assert h1 == h2

    def test_inequality(self):
        base = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        assert base != FileHandle(id="h_101", path=PATH, mode=RO, agentId=AGENT_ID)
        assert base != FileHandle(
            id=ID, path="/different.txt", mode=RO, agentId=AGENT_ID
        )
        assert base != FileHandle(id=ID, path=PATH, mode=RW, agentId=AGENT_ID)
        assert base != FileHandle(id=ID, path=PATH, mode=RO, agentId="agent_2")
        assert base is not None
        assert base != {"id": ID, "path": PATH, "mode": RO, "agentId": AGENT_ID}

    def test_hashability(self):
        h1 = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        h2 = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        h3 = FileHandle(id="different", path=PATH, mode=RO, agentId=AGENT_ID)

        assert hash(h1) == hash(h2)
        assert len({h1, h2, h3}) == 2


class TestFileHandleEdgeCases:
    def test_repr_and_str(self):
        handle = FileHandle(id=ID, path=PATH, mode=RO, agentId=AGENT_ID)
        r = repr(handle)

        assert ID in r and PATH in r and RO in r and AGENT_ID in r
        assert isinstance(str(handle), str) and len(str(handle)) > 0

    def test_unicode_and_special_characters(self):
        unicode_path = "/podaci/šarena_datoteka.txt"
        unicode_agent = "agent_čćž"

        handle = FileHandle(id=ID, path=unicode_path, mode=RW, agentId=unicode_agent)
        assert handle.path == unicode_path
        assert handle.agentId == unicode_agent
