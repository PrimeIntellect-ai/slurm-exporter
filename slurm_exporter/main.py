"""Main entry point for SLURM Prometheus exporter."""

import argparse
import os
import time

from prometheus_client import REGISTRY, start_http_server

from .collector import SlurmCollector
from .slurm_client import SlurmClient


def main():
    parser = argparse.ArgumentParser(
        description="Prometheus exporter for SLURM cluster metrics"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SLURM_EXPORTER_PORT", "9341")),
        help="Port to expose metrics on (default: 9341)",
    )
    parser.add_argument(
        "--bind",
        default=os.environ.get("SLURM_EXPORTER_BIND", "127.0.0.1"),
        help="Address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--cluster",
        default=os.environ.get("SLURM_CLUSTER_NAME", "default"),
        help="Cluster name label (default: default)",
    )
    args = parser.parse_args()

    slurm_client = SlurmClient()
    collector = SlurmCollector(slurm_client, args.cluster)
    REGISTRY.register(collector)

    print(f"Starting SLURM exporter on {args.bind}:{args.port}")
    print(f"Cluster name: {args.cluster}")

    start_http_server(args.port, addr=args.bind)

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
