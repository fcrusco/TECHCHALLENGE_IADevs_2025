terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
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
  name     = "tech_challenge_fiap_2"
  location = "Brazil South"
}

# =========================
# Storage Account
# =========================
resource "azurerm_storage_account" "storage" {
  name                     = "techchallfiapfase201"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  public_network_access_enabled = true

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }
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
  name                = "ASP-techchallengefiap2-8876"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type  = "Linux"
  sku_name = "B1"
}

# =========================
# App Service (Web App - API)
# =========================
resource "azurerm_linux_web_app" "app" {
  name                = "fiap-techchallengefiap-fase2"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.app_plan.id

  site_config {
    application_stack {
      python_version = "3.10"
    }

    always_on = true
    app_command_line = "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
  }

  app_settings = {
    AZURE_STORAGE_CONNECTION_STRING = azurerm_storage_account.storage.primary_connection_string
    SCM_DO_BUILD_DURING_DEPLOYMENT  = "true"
    ENABLE_ORYX_BUILD               = "true"
    PYTHON_ENABLE_WORKER_EXTENSIONS = "1"
    WEBSITE_PYTHON_DEFAULT_VERSION  = "3.10"
    WEBSITES_PORT                   = "8000"
    WEBSITES_CONTAINER_START_TIME_LIMIT = "1800"
    # Adicione esta linha:
    OPENAI_API_KEY                  = "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"
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }
}

# =========================
# App Service (Web App - Frontend)
# =========================
resource "azurerm_linux_web_app" "frontend" {
  name                = "fiap-techchallengefiap-fase2-front"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.app_plan.id

  site_config {
    application_stack {
      python_version = "3.10"
    }

    always_on = true
    app_command_line = "python server.py"

    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
  }

  app_settings = {
    API_BASE_URL                     = "https://${azurerm_linux_web_app.app.default_hostname}"
    SCM_DO_BUILD_DURING_DEPLOYMENT  = "true"
    ENABLE_ORYX_BUILD               = "true"
    PYTHON_ENABLE_WORKER_EXTENSIONS = "1"
    WEBSITE_PYTHON_DEFAULT_VERSION  = "3.10"
    PORT                            = "8000"
    WEBSITES_PORT                   = "8000"
    PYTHON_ENABLE_GUNICORN_MULTI_WORKERS = "true"
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }
}

# =========================
# Outputs
# =========================
output "api_url" {
  value = "https://${azurerm_linux_web_app.app.default_hostname}"
}

output "api_health_check_url" {
  value = "https://${azurerm_linux_web_app.app.default_hostname}/health"
}

output "api_docs_url" {
  value = "https://${azurerm_linux_web_app.app.default_hostname}/docs"
}

output "api_redoc_url" {
  value = "https://${azurerm_linux_web_app.app.default_hostname}/redoc"
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}

output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "frontend_url" {
  value = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}
