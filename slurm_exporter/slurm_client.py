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
        # Get all jobs with specific format for easy parsing
        # %i=job_id, %T=state, %C=cpus, %m=min_memory, %D=nodes, %b=gres, %N=nodelist
        output = self._run_command([
            "squeue",
            "--all",
            "--noheader",
            "--Format=JobID:|,State:|,NumCPUs:|,MinMemoryNode:|,NumNodes:|,Gres:|,NodeList:|,Partition:|",
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
        if len(parts) < 7:
            return None

        job_id = parts[0].strip()
        if not job_id:
            return None

        mem_str = parts[3].strip()
        mem_mb = self._parse_memory(mem_str)

        return {
            "job_id": job_id,
            "job_state": [parts[1].strip()],
            "cpus": int(parts[2].strip() or 0),
            "memory_per_node": {"number": mem_mb},
            "node_count": {"number": int(parts[4].strip() or 0)},
            "tres_alloc_str": self._gres_to_tres(parts[5].strip()),
            "nodelist": parts[6].strip(),
            "partition": parts[7].strip() if len(parts) > 7 else "",
        }

    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string like '4G', '512M', '1T' to MB."""
        if not mem_str:
            return 0
        mem_str = mem_str.upper()
        try:
            if mem_str.endswith("T"):
                return int(float(mem_str[:-1]) * 1024 * 1024)
            elif mem_str.endswith("G"):
                return int(float(mem_str[:-1]) * 1024)
            elif mem_str.endswith("M"):
                return int(float(mem_str[:-1]))
            elif mem_str.endswith("K"):
                return int(float(mem_str[:-1]) / 1024)
            else:
                return int(mem_str)
        except ValueError:
            return 0

    def _gres_to_tres(self, gres: str) -> str:
        """Convert GRES format to TRES format for GPU parsing.

        GRES: gpu:a100:2 -> TRES: gres/gpu:a100=2
        """
        if not gres or gres == "(null)":
            return ""

        tres_parts = []
        for item in gres.split(","):
            item = item.strip()
            if not item.startswith("gpu"):
                continue
            parts = item.split(":")
            if len(parts) == 2:
                # gpu:N
                tres_parts.append(f"gres/gpu={parts[1]}")
            elif len(parts) >= 3:
                # gpu:type:N
                tres_parts.append(f"gres/gpu:{parts[1]}={parts[2]}")
        return ",".join(tres_parts)
