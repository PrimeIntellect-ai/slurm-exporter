"""Tests for SlurmCollector."""

import pytest
from unittest.mock import MagicMock, patch

from slurm_exporter.collector import SlurmCollector


def make_collector():
    client = MagicMock()
    return SlurmCollector(client, "test-cluster"), client


def collect_all(collector):
    return list(collector.collect())


class TestNodeMetrics:
    def test_returns_metrics_when_nodes_available(self):
        collector, client = make_collector()
        client.get_nodes.return_value = [
            {"name": "node1", "state": ["IDLE"]},
            {"name": "node2", "state": ["ALLOCATED"]},
            {"name": "node3", "state": ["IDLE"]},
        ]
        client.get_jobs.return_value = []

        metrics = collect_all(collector)
        names = {m.name for m in metrics}
        assert "slurm_nodes" in names
        assert "slurm_node_state" in names

    def test_node_state_counts_aggregated(self):
        collector, client = make_collector()
        client.get_nodes.return_value = [
            {"name": "node1", "state": ["IDLE"]},
            {"name": "node2", "state": ["IDLE"]},
            {"name": "node3", "state": ["ALLOCATED"]},
        ]
        client.get_jobs.return_value = []

        nodes_metric = next(m for m in collect_all(collector) if m.name == "slurm_nodes")
        samples = {tuple(s.labels.values()): s.value for s in nodes_metric.samples}
        assert samples[("test-cluster", "idle")] == 2.0
        assert samples[("test-cluster", "allocated")] == 1.0

    def test_exits_on_get_nodes_failure(self):
        collector, client = make_collector()
        client.get_nodes.side_effect = RuntimeError("scontrol: connection refused")

        with patch("slurm_exporter.collector.os._exit", side_effect=SystemExit(1)) as mock_exit:
            with pytest.raises(SystemExit):
                collect_all(collector)
            mock_exit.assert_called_once_with(1)

    def test_exits_on_get_jobs_failure(self):
        collector, client = make_collector()
        client.get_nodes.return_value = []
        client.get_jobs.side_effect = RuntimeError("squeue: connection refused")

        with patch("slurm_exporter.collector.os._exit", side_effect=SystemExit(1)) as mock_exit:
            with pytest.raises(SystemExit):
                collect_all(collector)
            mock_exit.assert_called_once_with(1)

    def test_combined_node_states_joined(self):
        collector, client = make_collector()
        client.get_nodes.return_value = [
            {"name": "node1", "state": ["MIXED", "DRAIN"]},
        ]
        client.get_jobs.return_value = []

        node_state_metric = next(m for m in collect_all(collector) if m.name == "slurm_node_state")
        states = [s.labels["state"] for s in node_state_metric.samples]
        assert "mixed+drain" in states


class TestJobMetrics:
    def test_returns_metrics_when_jobs_available(self):
        collector, client = make_collector()
        client.get_nodes.return_value = []
        client.get_jobs.return_value = [
            {"job_state": ["RUNNING"], "user": "alice", "name": "train"},
            {"job_state": ["PENDING"], "user": "bob", "name": "eval"},
        ]

        metrics = collect_all(collector)
        names = {m.name for m in metrics}
        assert "slurm_jobs" in names

    def test_job_state_counts_aggregated(self):
        collector, client = make_collector()
        client.get_nodes.return_value = []
        client.get_jobs.return_value = [
            {"job_state": ["RUNNING"], "user": "alice", "name": "train"},
            {"job_state": ["RUNNING"], "user": "alice", "name": "train"},
            {"job_state": ["PENDING"], "user": "bob", "name": "eval"},
        ]

        jobs_metric = next(m for m in collect_all(collector) if m.name == "slurm_jobs")
        samples = {(s.labels["state"], s.labels["user"], s.labels["name"]): s.value for s in jobs_metric.samples}
        assert samples[("running", "alice", "train")] == 2.0
        assert samples[("pending", "bob", "eval")] == 1.0

    def test_empty_nodes_and_jobs_returns_empty_metrics(self):
        collector, client = make_collector()
        client.get_nodes.return_value = []
        client.get_jobs.return_value = []

        metrics = collect_all(collector)
        assert len(metrics) == 3  # slurm_nodes, slurm_node_state, slurm_jobs
        for m in metrics:
            assert m.samples == []
