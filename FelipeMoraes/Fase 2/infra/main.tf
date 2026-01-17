provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "techchallenge-iadt-rg"
  location = "East US"
}

resource "azurerm_app_service_plan" "plan" {
  name                = "techchallenge-plan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Free"
    size = "F1"
  }
}
