"""Prometheus collector for SLURM metrics."""

from prometheus_client.core import GaugeMetricFamily
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
        nodes_by_state = GaugeMetricFamily(
            "slurm_nodes",
            "Number of nodes by state",
            labels=["cluster", "state"],
        )

        try:
            nodes = self.slurm_client.get_nodes()
        except Exception as e:
            print(f"Error fetching nodes: {e}")
            nodes = []

        state_counts: dict[str, int] = {}

        for node in nodes:
            state = self._parse_node_state(node.get("state", []))
            state_counts[state] = state_counts.get(state, 0) + 1

        for state, count in state_counts.items():
            nodes_by_state.add_metric([self.cluster_name, state], count)

        yield nodes_by_state

    def _collect_job_metrics(self):
        jobs_by_state = GaugeMetricFamily(
            "slurm_jobs",
            "Number of jobs by state, user, and name",
            labels=["cluster", "state", "user", "name"],
        )

        try:
            jobs = self.slurm_client.get_jobs()
        except Exception as e:
            print(f"Error fetching jobs: {e}")
            jobs = []

        state_user_name_counts: dict[tuple[str, str, str], int] = {}

        for job in jobs:
            state = self._parse_job_state(job.get("job_state", []))
            user = job.get("user", "unknown")
            name = job.get("name", "unknown")
            key = (state, user, name)
            state_user_name_counts[key] = state_user_name_counts.get(key, 0) + 1

        for (state, user, name), count in state_user_name_counts.items():
            jobs_by_state.add_metric([self.cluster_name, state, user, name], count)

        yield jobs_by_state

    def _parse_node_state(self, state: list | str) -> str:
        if isinstance(state, list):
            return "+".join(state).lower() if state else "unknown"
        return str(state).lower()

    def _parse_job_state(self, state: list | str) -> str:
        if isinstance(state, list):
            return state[0].lower() if state else "unknown"
        return str(state).lower()
