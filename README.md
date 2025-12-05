# SLURM Prometheus Exporter

A Prometheus exporter for SLURM cluster metrics. Collects aggregate node and job counts by state using `scontrol` and `squeue` CLI commands.

## Usage

### Docker

```bash
docker run -d \
  --name slurm-exporter \
  --network host \
  -v /data/slurm:/data/slurm:ro \
  -v /var/run/munge:/var/run/munge:ro \
  -e SLURM_CONF=/data/slurm/etc/slurm.conf \
  ghcr.io/primeintellect-ai/slurm-exporter:latest \
  --cluster mycluster
```

### Local

```bash
# Install
uv sync

# Run
uv run slurm-exporter --cluster mycluster --port 9341
```

## Configuration

| Flag | Environment Variable | Default | Description |
|------|---------------------|---------|-------------|
| `--port` | `SLURM_EXPORTER_PORT` | `9341` | Port to expose metrics on |
| `--bind` | `SLURM_EXPORTER_BIND` | `127.0.0.1` | Address to bind to |
| `--cluster` | `SLURM_CLUSTER_NAME` | `default` | Cluster name label |

## Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `slurm_nodes` | Gauge | `cluster`, `state` | Number of nodes by state |
| `slurm_jobs` | Gauge | `cluster`, `state`, `user`, `name` | Number of jobs by state, user, and name |

### Node States

Common node states: `idle`, `allocated`, `mixed`, `down`, `drained`, `draining`

### Job States

Common job states: `running`, `pending`, `completed`, `failed`, `cancelled`, `timeout`

## Example PromQL Queries

```promql
# Total nodes by state
slurm_nodes

# Node utilization (allocated / total)
sum(slurm_nodes{state="allocated"}) / sum(slurm_nodes) * 100

# Running jobs
slurm_jobs{state="running"}

# Pending jobs
slurm_jobs{state="pending"}

# Jobs by user
sum by (user) (slurm_jobs{state="running"})

# Idle nodes
slurm_nodes{state="idle"}

# Problematic nodes (down, drained)
slurm_nodes{state=~"down|drained|draining"}
```

## Building

```bash
# Build with Docker Bake
docker buildx bake

# Push to registry
docker buildx bake --push
```

## License

MIT
