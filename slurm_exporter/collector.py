"""Prometheus collector for SLURM metrics."""

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_client.registry import Collector

from .slurm_client import SlurmClient


class SlurmCollector(Collector):
    """Collector that fetches SLURM metrics on each scrape."""

    def __init__(self, slurm_client: SlurmClient, cluster_name: str):
        self.slurm_client = slurm_client
        self.cluster_name = cluster_name

    def collect(self):
        yield from self._collect_node_metrics()
        yield from self._collect_job_metrics()

    def _collect_node_metrics(self):
        node_state = GaugeMetricFamily(
            "slurm_node_state",
            "SLURM node state (1 if node is in this state)",
            labels=["cluster", "node", "state"],
        )
        node_cpus_total = GaugeMetricFamily(
            "slurm_node_cpus_total",
            "Total CPUs on the node",
            labels=["cluster", "node"],
        )
        node_cpus_alloc = GaugeMetricFamily(
            "slurm_node_cpus_allocated",
            "Allocated CPUs on the node",
            labels=["cluster", "node"],
        )
        node_memory_total = GaugeMetricFamily(
            "slurm_node_memory_total_bytes",
            "Total memory on the node in bytes",
            labels=["cluster", "node"],
        )
        node_memory_alloc = GaugeMetricFamily(
            "slurm_node_memory_allocated_bytes",
            "Allocated memory on the node in bytes",
            labels=["cluster", "node"],
        )
        node_gpus_total = GaugeMetricFamily(
            "slurm_node_gpus_total",
            "Total GPUs on the node",
            labels=["cluster", "node", "gpu_type"],
        )
        node_gpus_alloc = GaugeMetricFamily(
            "slurm_node_gpus_allocated",
            "Allocated GPUs on the node",
            labels=["cluster", "node", "gpu_type"],
        )

        try:
            nodes = self.slurm_client.get_nodes()
        except Exception as e:
            print(f"Error fetching nodes: {e}")
            nodes = []

        for node in nodes:
            node_name = node.get("name", "unknown")
            state = self._parse_node_state(node.get("state", []))

            node_state.add_metric([self.cluster_name, node_name, state], 1)
            node_cpus_total.add_metric(
                [self.cluster_name, node_name],
                node.get("cpus", 0),
            )
            node_cpus_alloc.add_metric(
                [self.cluster_name, node_name],
                node.get("alloc_cpus", 0),
            )
            mem_total = node.get("real_memory", 0) * 1024 * 1024  # MB to bytes
            mem_alloc = node.get("alloc_memory", 0) * 1024 * 1024
            node_memory_total.add_metric([self.cluster_name, node_name], mem_total)
            node_memory_alloc.add_metric([self.cluster_name, node_name], mem_alloc)

            gpus_total, gpus_alloc = self._parse_gres(node)
            for gpu_type, count in gpus_total.items():
                node_gpus_total.add_metric(
                    [self.cluster_name, node_name, gpu_type], count
                )
            for gpu_type, count in gpus_alloc.items():
                node_gpus_alloc.add_metric(
                    [self.cluster_name, node_name, gpu_type], count
                )

        yield node_state
        yield node_cpus_total
        yield node_cpus_alloc
        yield node_memory_total
        yield node_memory_alloc
        yield node_gpus_total
        yield node_gpus_alloc

    def _collect_job_metrics(self):
        job_state = GaugeMetricFamily(
            "slurm_job_state",
            "SLURM job state (1 if job is in this state)",
            labels=["cluster", "job", "state"],
        )
        jobs_by_state = CounterMetricFamily(
            "slurm_jobs_total",
            "Total number of jobs by state",
            labels=["cluster", "state"],
        )
        job_cpus = GaugeMetricFamily(
            "slurm_job_cpus",
            "Number of CPUs allocated to the job",
            labels=["cluster", "job", "state"],
        )
        job_memory = GaugeMetricFamily(
            "slurm_job_memory_bytes",
            "Memory allocated to the job in bytes",
            labels=["cluster", "job", "state"],
        )
        job_gpus = GaugeMetricFamily(
            "slurm_job_gpus",
            "Number of GPUs allocated to the job",
            labels=["cluster", "job", "state", "gpu_type"],
        )
        job_nodes = GaugeMetricFamily(
            "slurm_job_nodes",
            "Number of nodes allocated to the job",
            labels=["cluster", "job", "state"],
        )

        try:
            jobs = self.slurm_client.get_jobs()
        except Exception as e:
            print(f"Error fetching jobs: {e}")
            jobs = []

        state_counts: dict[str, int] = {}

        for job in jobs:
            job_id = str(job.get("job_id", "unknown"))
            state = self._parse_job_state(job.get("job_state", []))

            job_state.add_metric([self.cluster_name, job_id, state], 1)
            state_counts[state] = state_counts.get(state, 0) + 1

            cpus = job.get("cpus", {}).get("number", 0) if isinstance(job.get("cpus"), dict) else job.get("cpus", 0)
            job_cpus.add_metric([self.cluster_name, job_id, state], cpus)

            mem_per_node = job.get("memory_per_node", {})
            if isinstance(mem_per_node, dict) and mem_per_node.get("number"):
                mem_bytes = mem_per_node.get("number", 0) * 1024 * 1024
            else:
                mem_per_cpu = job.get("memory_per_cpu", {})
                if isinstance(mem_per_cpu, dict) and mem_per_cpu.get("number"):
                    mem_bytes = mem_per_cpu.get("number", 0) * cpus * 1024 * 1024
                else:
                    mem_bytes = 0
            job_memory.add_metric([self.cluster_name, job_id, state], mem_bytes)

            node_count = job.get("node_count", {}).get("number", 0) if isinstance(job.get("node_count"), dict) else job.get("node_count", 0)
            job_nodes.add_metric([self.cluster_name, job_id, state], node_count)

            tres_alloc = job.get("tres_alloc_str", "") or job.get("tres_req_str", "")
            gpu_allocs = self._parse_tres_gpus(tres_alloc)
            for gpu_type, count in gpu_allocs.items():
                job_gpus.add_metric([self.cluster_name, job_id, state, gpu_type], count)

        for state, count in state_counts.items():
            jobs_by_state.add_metric([self.cluster_name, state], count)

        yield job_state
        yield jobs_by_state
        yield job_cpus
        yield job_memory
        yield job_gpus
        yield job_nodes

    def _parse_node_state(self, state: list | str) -> str:
        if isinstance(state, list):
            return "+".join(state).lower() if state else "unknown"
        return str(state).lower()

    def _parse_job_state(self, state: list | str) -> str:
        if isinstance(state, list):
            return state[0].lower() if state else "unknown"
        return str(state).lower()

    def _parse_gres(
        self, node: dict
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Parse GRES (generic resources) to extract GPU info.

        Returns (total_gpus, allocated_gpus) as dicts of {gpu_type: count}.
        GRES format examples: "gpu:a100:4", "gpu:2", "gpu:v100:8(S:0-1)"
        """
        total: dict[str, int] = {}
        alloc: dict[str, int] = {}

        gres = node.get("gres", "")
        gres_used = node.get("gres_used", "")

        for gpu_type, count in self._parse_gres_string(gres):
            total[gpu_type] = total.get(gpu_type, 0) + count

        for gpu_type, count in self._parse_gres_string(gres_used):
            alloc[gpu_type] = alloc.get(gpu_type, 0) + count

        return total, alloc

    def _parse_gres_string(self, gres: str) -> list[tuple[str, int]]:
        """Parse a GRES string and return list of (gpu_type, count) tuples."""
        results = []
        if not gres:
            return results

        for item in gres.split(","):
            item = item.strip()
            if not item.startswith("gpu:"):
                continue

            parts = item[4:].split(":")  # Remove "gpu:" prefix
            if len(parts) == 1:
                # Format: gpu:N or gpu:N(IDX)
                count_str = parts[0].split("(")[0]
                try:
                    results.append(("gpu", int(count_str)))
                except ValueError:
                    # Format might be gpu:type with no count, assume 1
                    results.append((parts[0], 1))
            else:
                # Format: gpu:type:N or gpu:type:N(IDX)
                gpu_type = parts[0]
                count_str = parts[1].split("(")[0]
                try:
                    results.append((gpu_type, int(count_str)))
                except ValueError:
                    pass

        return results

    def _parse_tres_gpus(self, tres_str: str) -> dict[str, int]:
        """Parse TRES string to extract GPU allocations.

        TRES format: "cpu=4,mem=16G,node=1,gres/gpu=2" or "gres/gpu:a100=4"
        """
        gpus: dict[str, int] = {}
        if not tres_str:
            return gpus

        for item in tres_str.split(","):
            item = item.strip()
            if "gres/gpu" not in item:
                continue

            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            try:
                count = int(value)
            except ValueError:
                continue

            if key == "gres/gpu":
                gpus["gpu"] = gpus.get("gpu", 0) + count
            elif key.startswith("gres/gpu:"):
                gpu_type = key.split(":")[1]
                gpus[gpu_type] = gpus.get(gpu_type, 0) + count

        return gpus
