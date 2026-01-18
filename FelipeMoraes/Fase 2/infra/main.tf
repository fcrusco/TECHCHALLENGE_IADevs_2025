terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# =========================
# Resource Group
# =========================
resource "azurerm_resource_group" "rg" {
  name     = "tech_challenge_2"
  location = "Brazil South"
}

# =========================
# Storage Account
# =========================
resource "azurerm_storage_account" "storage" {
  name                     = "techchallfase201"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  allow_blob_public_access = false
}

resource "azurerm_storage_container" "modelos" {
  name                  = "modelos"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# =========================
# App Service Plan (Linux)
# =========================
resource "azurerm_service_plan" "app_plan" {
  name                = "ASP-techchallenge2-8876"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type  = "Linux"
  sku_name = "F1" # Azure for Students
}

# =========================
# App Service (Web App)
# =========================
resource "azurerm_linux_web_app" "app" {
  name                = "fiap-techchallenge-fase2"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.app_plan.id

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }

  app_settings = {
    AZURE_STORAGE_CONNECTION_STRING = azurerm_storage_account.storage.primary_connection_string
  }
}
