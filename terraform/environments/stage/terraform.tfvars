# Terraform variables for the STAGING environment
# A mid-tier configuration for pre-production testing.

environment         = "staging"
resource_group_name = "trading-system-staging-rg"
location            = "eastus"

# A mid-tier container for testing
container_cpu    = 2.0
container_memory = 4.0
restart_policy   = "Always"
log_level        = "INFO"
storage_quota_gb = 50

# Use a specific versioned Docker image
docker_image      = "youracr.azurecr.io/trading-system:staging-v1.2" # Replace with your ACR
ticker_to_analyze = "TSLA"
