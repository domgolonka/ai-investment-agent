# Terraform variables for the DEVELOPMENT environment
# Optimized for cost efficiency and rapid iteration.

environment         = "dev"
resource_group_name = "trading-system-dev-rg"
location            = "eastus"

# Use a smaller, cheaper container for development
container_cpu    = 1.0
container_memory = 2.0
restart_policy   = "OnFailure"
log_level        = "DEBUG"
storage_quota_gb = 10

# The Docker image tag can be 'latest' for dev builds
docker_image      = "youracr.azurecr.io/trading-system:latest" # Replace with your ACR
ticker_to_analyze = "NVDA"
