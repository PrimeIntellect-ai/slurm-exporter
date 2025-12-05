"""SLURM CLI client using scontrol and squeue."""

import subprocess
from typing import Any


class SlurmClient:
    """Client for interacting with SLURM via CLI commands."""

    def __init__(self):
        pass

    def _run_command(self, cmd: list[str]) -> str:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result.check_returncode()
        return result.stdout

    def get_nodes(self) -> list[dict[str, Any]]:
        """Fetch all nodes using scontrol."""
        output = self._run_command(["scontrol", "show", "nodes", "-o"])
        nodes = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            node = self._parse_scontrol_line(line)
            if node:
                nodes.append(node)
        return nodes

    def get_jobs(self) -> list[dict[str, Any]]:
        """Fetch all jobs using squeue."""
        output = self._run_command([
            "squeue",
            "--all",
            "--noheader",
            "--Format=JobID:|,State:|,UserName:|,Name:|",
        ])
        jobs = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            job = self._parse_squeue_line(line)
            if job:
                jobs.append(job)
        return jobs

    def _parse_scontrol_line(self, line: str) -> dict[str, Any] | None:
        """Parse a single line from scontrol show nodes -o."""
        data: dict[str, Any] = {}
        for item in line.split():
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            data[key] = value

        if not data.get("NodeName"):
            return None

        return {
            "name": data.get("NodeName", ""),
            "state": data.get("State", "UNKNOWN").split("+"),
            "cpus": int(data.get("CPUTot", 0)),
            "alloc_cpus": int(data.get("CPUAlloc", 0)),
            "real_memory": int(data.get("RealMemory", 0)),
            "alloc_memory": int(data.get("AllocMem", 0)),
            "gres": data.get("Gres", ""),
            "gres_used": data.get("GresUsed", ""),
        }

    def _parse_squeue_line(self, line: str) -> dict[str, Any] | None:
        """Parse a single line from squeue output."""
        parts = line.split("|")
        if len(parts) < 4:
            return None

        job_id = parts[0].strip()
        if not job_id:
            return None

        return {
            "job_id": job_id,
            "job_state": [parts[1].strip()],
            "user": parts[2].strip(),
            "name": parts[3].strip(),
        }
