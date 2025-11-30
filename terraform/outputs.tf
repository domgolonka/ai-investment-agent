# Description: This file defines the outputs that will be displayed after a
# successful Terraform deployment. These outputs provide easy access to key
# information about the created resources, such as names, IDs, and connection strings.

output "resource_group_name" {
  description = "The name of the deployed resource group."
  value       = azurerm_resource_group.main.name
}

output "container_group_name" {
  description = "The name of the Azure Container Instance group."
  value       = azurerm_container_group.main.name
}

output "container_group_fqdn" {
  description = "The fully qualified domain name (FQDN) of the container group."
  value       = azurerm_container_group.main.fqdn
}

output "container_group_ip_address" {
  description = "The public IP address of the container group."
  value       = azurerm_container_group.main.ip_address
}

output "storage_account_name" {
  description = "The name of the storage account used for agent memory."
  value       = azurerm_storage_account.main.name
}

output "log_analytics_workspace_name" {
  description = "The name of the Log Analytics Workspace for monitoring."
  value       = azurerm_log_analytics_workspace.main.name
}

output "application_insights_connection_string" {
  description = "The connection string for Application Insights."
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights."
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}
