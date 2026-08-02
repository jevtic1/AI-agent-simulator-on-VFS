import json

import pytest

from src.models_Agent import Agent
from src.models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    ReadOp,
    ThinkOp,
    WriteOp,
)
from src.util_Parser import Parser
from src.vfs_Mount import Mount


@pytest.fixture
def valid_json_data():
    return {
        "settings": {"max_running_agents": 2},
        "vfs": {
            "mounts": [
                {"source": "input/shared", "target": "/shared", "mode": "ro"},
                {"source": "input/work", "target": "/work", "mode": "rw"},
            ]
        },
        "agents": [
            {
                "id": "A1",
                "priority": 1,
                "arrival_time": 0,
                "operations": [
                    {"type": "THINK", "duration": 3},
                    {
                        "type": "OPEN",
                        "path": "/shared/a.txt",
                        "mode": "read",
                        "handle": "f",
                    },
                    {"type": "READ", "handle": "f"},
                    {"type": "CLOSE", "handle": "f"},
                    {
                        "type": "OPEN",
                        "path": "/work/result.txt",
                        "mode": "append",
                        "handle": "out",
                    },
                    {"type": "WRITE", "handle": "out", "data": "hello"},
                    {"type": "APPEND", "handle": "out", "data": "world"},
                    {"type": "CLOSE", "handle": "out"},
                ],
            }
        ],
    }


@pytest.fixture
def valid_json_file(tmp_path, valid_json_data):
    file_path = tmp_path / "config.json"
    file_path.write_text(json.dumps(valid_json_data))
    return file_path


class TestParser:
    def test_parse_valid_config_structure(self, valid_json_file):
        config = Parser.parse_file(str(valid_json_file))

        assert hasattr(config, "max_running_agents")
        assert hasattr(config, "mounts")
        assert hasattr(config, "agents")

        assert config.max_running_agents == 2
        assert len(config.mounts) == 2
        assert len(config.agents) == 1

    def test_parse_mounts(self, valid_json_file):
        config = Parser.parse_file(str(valid_json_file))

        m1, m2 = config.mounts
        assert isinstance(m1, Mount)
        assert m1.source == "input/shared"
        assert m1.target == "/shared"
        assert m1.mode == "ro"

        assert isinstance(m2, Mount)
        assert m2.source == "input/work"
        assert m2.target == "/work"
        assert m2.mode == "rw"

    def test_parse_agent_and_operations(self, valid_json_file):
        config = Parser.parse_file(str(valid_json_file))

        agent = config.agents[0]
        assert isinstance(agent, Agent)
        assert agent.id == "A1"
        assert agent.priority == 1
        assert agent.arrival_time == 0
        assert len(agent.operations) == 8

        ops = agent.operations
        assert isinstance(ops[0], ThinkOp)
        assert ops[0].duration == 3

        assert isinstance(ops[1], OpenOp)
        assert ops[1].path == "/shared/a.txt"
        assert ops[1].mode == "read"
        assert ops[1].handle == "f"

        assert isinstance(ops[2], ReadOp)
        assert ops[2].handle == "f"

        assert isinstance(ops[3], CloseOp)
        assert ops[3].handle == "f"

        assert isinstance(ops[4], OpenOp)
        assert ops[4].path == "/work/result.txt"
        assert ops[4].mode == "append"
        assert ops[4].handle == "out"

        assert isinstance(ops[5], WriteOp)
        assert ops[5].handle == "out"
        assert ops[5].data == "hello"

        assert isinstance(ops[6], AppendOp)
        assert ops[6].handle == "out"
        assert ops[6].data == "world"

        assert isinstance(ops[7], CloseOp)
        assert ops[7].handle == "out"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Parser.parse_file("non_existent_file.json")

    def test_malformed_json_syntax(self, tmp_path):
        file_path = tmp_path / "bad_syntax.json"
        file_path.write_text("{ settings: { max_running_agents: 2 } ")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            Parser.parse_file(str(file_path))

    @pytest.mark.parametrize("missing_key", ["settings", "vfs", "agents"])
    def test_missing_top_level_sections(self, tmp_path, valid_json_data, missing_key):
        del valid_json_data[missing_key]
        file_path = tmp_path / "missing_section.json"
        file_path.write_text(json.dumps(valid_json_data))

        with pytest.raises((KeyError, ValueError)):
            Parser.parse_file(str(file_path))

    @pytest.mark.parametrize("invalid_val", [0, -1, -10])
    def test_invalid_max_running_agents(self, tmp_path, valid_json_data, invalid_val):
        valid_json_data["settings"]["max_running_agents"] = invalid_val
        file_path = tmp_path / "bad_settings.json"
        file_path.write_text(json.dumps(valid_json_data))

        with pytest.raises(ValueError):
            Parser.parse_file(str(file_path))

    def test_unknown_operation_type(self, tmp_path, valid_json_data):
        valid_json_data["agents"][0]["operations"].append({"type": "UNKNOWN_OP"})
        file_path = tmp_path / "bad_op.json"
        file_path.write_text(json.dumps(valid_json_data))

        with pytest.raises(ValueError):
            Parser.parse_file(str(file_path))

    @pytest.mark.parametrize(
        "missing_op_field",
        [
            {"type": "THINK"},
            {"type": "OPEN", "path": "/a.txt", "mode": "read"},
            {"type": "READ"},
            {"type": "WRITE", "handle": "h1"},
            {"type": "APPEND", "handle": "h1"},
            {"type": "CLOSE"},
        ],
    )
    def test_missing_operation_fields(
        self, tmp_path, valid_json_data, missing_op_field
    ):
        valid_json_data["agents"][0]["operations"] = [missing_op_field]
        file_path = tmp_path / "incomplete_op.json"
        file_path.write_text(json.dumps(valid_json_data))

        with pytest.raises((KeyError, ValueError, TypeError)):
            Parser.parse_file(str(file_path))
