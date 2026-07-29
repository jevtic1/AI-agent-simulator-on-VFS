import json
from dataclasses import dataclass

from src.models_Agent import Agent
from src.models_Operations import (
    AppendOp,
    CloseOp,
    OpenOp,
    ReadOp,
    ThinkOp,
    WriteOp,
)
from src.vfs_Mount import Mount


@dataclass
class Config:
    max_running_agents: int
    mounts: list
    agents: list


class Parser:
    @staticmethod
    def parse_file(file_path: str) -> Config:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "settings" not in data or "vfs" not in data or "agents" not in data:
            raise KeyError("Missing required top-level section.")

        max_agents = data["settings"].get("max_running_agents")
        if max_agents is None or max_agents <= 0:
            raise ValueError("max_running_agents must be greater than 0.")

        mounts = [
            Mount(source=m["source"], target=m["target"], mode=m["mode"])
            for m in data["vfs"].get("mounts", [])
        ]

        agents = []
        for raw_agent in data["agents"]:
            ops = []
            for op in raw_agent.get("operations", []):
                op_type = op.get("type")
                if op_type == "THINK":
                    ops.append(ThinkOp(duration=op["duration"]))
                elif op_type == "OPEN":
                    ops.append(
                        OpenOp(path=op["path"], mode=op["mode"], handle=op["handle"])
                    )
                elif op_type == "READ":
                    ops.append(ReadOp(handle=op["handle"]))
                elif op_type == "WRITE":
                    ops.append(WriteOp(handle=op["handle"], data=op["data"]))
                elif op_type == "APPEND":
                    ops.append(AppendOp(handle=op["handle"], data=op["data"]))
                elif op_type == "CLOSE":
                    ops.append(CloseOp(handle=op["handle"]))
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")

            agents.append(
                Agent(
                    id=raw_agent["id"],
                    priority=raw_agent["priority"],
                    arrival_time=raw_agent["arrival_time"],
                    operations=ops,
                )
            )

        return Config(
            max_running_agents=max_agents,
            mounts=mounts,
            agents=agents,
        )
