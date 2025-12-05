# SLURM Prometheus Exporter

A Prometheus exporter for SLURM cluster metrics. Collects node and job information using `scontrol` and `squeue` CLI commands.

## Usage

### Docker

```bash
docker run -d \
  --name slurm-exporter \
  -p 9341:9341 \
  -v /etc/slurm:/etc/slurm:ro \
  -v /var/run/munge:/var/run/munge:ro \
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

### Node Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `slurm_node_state` | Gauge | `cluster`, `node`, `state` | SLURM node state (1 if node is in this state) |
| `slurm_node_cpus_total` | Gauge | `cluster`, `node` | Total CPUs on the node |
| `slurm_node_cpus_allocated` | Gauge | `cluster`, `node` | Allocated CPUs on the node |
| `slurm_node_memory_total_bytes` | Gauge | `cluster`, `node` | Total memory on the node in bytes |
| `slurm_node_memory_allocated_bytes` | Gauge | `cluster`, `node` | Allocated memory on the node in bytes |
| `slurm_node_gpus_total` | Gauge | `cluster`, `node`, `gpu_type` | Total GPUs on the node |
| `slurm_node_gpus_allocated` | Gauge | `cluster`, `node`, `gpu_type` | Allocated GPUs on the node |

### Job Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `slurm_job_state` | Gauge | `cluster`, `job`, `state` | SLURM job state (1 if job is in this state) |
| `slurm_jobs_total` | Counter | `cluster`, `state` | Total number of jobs by state |
| `slurm_job_cpus` | Gauge | `cluster`, `job`, `state` | Number of CPUs allocated to the job |
| `slurm_job_memory_bytes` | Gauge | `cluster`, `job`, `state` | Memory allocated to the job in bytes |
| `slurm_job_gpus` | Gauge | `cluster`, `job`, `state`, `gpu_type` | Number of GPUs allocated to the job |
| `slurm_job_nodes` | Gauge | `cluster`, `job`, `state` | Number of nodes allocated to the job |

## Example PromQL Queries

### Cluster Utilization

```promql
# CPU utilization percentage
sum(slurm_node_cpus_allocated{cluster="mycluster"}) / sum(slurm_node_cpus_total{cluster="mycluster"}) * 100

# Memory utilization percentage
sum(slurm_node_memory_allocated_bytes{cluster="mycluster"}) / sum(slurm_node_memory_total_bytes{cluster="mycluster"}) * 100

# GPU utilization percentage
sum(slurm_node_gpus_allocated) / sum(slurm_node_gpus_total) * 100

# GPU utilization by type
sum by (gpu_type) (slurm_node_gpus_allocated) / sum by (gpu_type) (slurm_node_gpus_total) * 100
```

### Job Statistics

```promql
# Jobs by state
slurm_jobs_total

# Running jobs count
slurm_jobs_total{state="running"}

# Pending jobs count
slurm_jobs_total{state="pending"}

# Total CPUs used by running jobs
sum(slurm_job_cpus{state="running"})
```

### Node Availability

```promql
# Count nodes by state
count by (state) (slurm_node_state)

# Idle nodes
count(slurm_node_state{state="idle"})

# Nodes with issues
count(slurm_node_state{state=~"down|drain|drained"})
```

## Building

```bash
# Build with Docker Bake
docker buildx bake

# Build with specific SLURM version
SLURM_TAG=slurm-24-05-4-1 docker buildx bake

# Push to registry
docker buildx bake --push
```

## License

MIT
