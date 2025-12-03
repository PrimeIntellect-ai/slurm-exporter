variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = "docker.io"
}

variable "IMAGE" {
  default = "primeintellect/slurm-exporter"
}

variable "SLURM_TAG" {
  default = "slurm-25-05-3-1"
}

group "default" {
  targets = ["slurm-exporter"]
}

target "slurm-exporter" {
  context    = "."
  dockerfile = "Dockerfile"
  args = {
    SLURM_TAG = "${SLURM_TAG}"
  }
  tags = [
    "${REGISTRY}/${IMAGE}:${TAG}",
  ]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "slurm-exporter-dev" {
  inherits = ["slurm-exporter"]
  tags = [
    "${REGISTRY}/${IMAGE}:dev",
  ]
  platforms = ["linux/amd64"]
}
