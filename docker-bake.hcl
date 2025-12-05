variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = "ghcr.io"
}

variable "IMAGE" {
  default = "primeintellect-ai/slurm-exporter"
}

group "default" {
  targets = ["slurm-exporter"]
}

target "slurm-exporter" {
  context    = "."
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE}:${TAG}",
  ]
  platforms = ["linux/amd64"]
}
