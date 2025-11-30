# Terraform variables for the PRODUCTION environment
# A more powerful configuration for production workloads.

environment         = "prod"
resource_group_name = "trading-system-prod-rg"
location            = "eastus"

# A more powerful container for production
container_cpu    = 4.0
container_memory = 8.0
restart_policy   = "Always"
log_level        = "INFO"
storage_quota_gb = 100

# Use a specific, tested versioned Docker image for production
docker_image      = "youracr.azurecr.io/trading-system:prod-v1.2.1" # Replace with your ACR
ticker_to_analyze = "SPY"
