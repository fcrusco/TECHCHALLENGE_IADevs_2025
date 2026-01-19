# 📋 Guia de Logs no Azure

Este documento explica onde os logs do sistema estão sendo gerados agora que a aplicação está hospedada no Azure App Service.

## 📍 Localização dos Logs

### Configuração Atual

Os logs estão configurados no arquivo `infra/main.tf` para serem armazenados no **sistema de arquivos do App Service**:

```terraform
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
```

### App Services Configurados

1. **API**: `fiap-techchallengefiap-fase2`
   - Logs de aplicação: Nível `Information`
   - Logs HTTP: Retenção de 7 dias, máximo 35MB

2. **Frontend**: `fiap-techchallengefiap-fase2-front`
   - Logs de aplicação: Nível `Information`
   - Logs HTTP: Retenção de 7 dias, máximo 35MB

## 🔍 Como Acessar os Logs

### 1. Via Azure Portal (Recomendado)

#### Log Stream (Tempo Real)

1. Acesse o [Azure Portal](https://portal.azure.com)
2. Navegue até **App Services**
3. Selecione o App Service desejado:
   - `fiap-techchallengefiap-fase2` (API)
   - `fiap-techchallengefiap-fase2-front` (Frontend)
4. No menu lateral, vá em **Monitoring** → **Log stream**
5. Os logs aparecerão em tempo real

#### Logs Históricos

1. No App Service, vá em **Monitoring** → **App Service logs**
2. Verifique se **Application Logging (Filesystem)** está habilitado
3. Acesse **Advanced Tools** → **Go** (Kudu)
4. Navegue até **Debug console** → **CMD**
5. Vá para a pasta `LogFiles`:
   ```
   LogFiles/
   ├── Application/
   │   └── logging-*.txt  (Logs da aplicação Python)
   └── http/
       └── RawLogs/       (Logs HTTP)
   ```

### 2. Via Kudu (SCM)

1. Acesse: `https://[nome-do-app].scm.azurewebsites.net`
   - API: `https://fiap-techchallengefiap-fase2.scm.azurewebsites.net`
   - Frontend: `https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net`

2. Vá em **Debug console** → **CMD**

3. Navegue até `LogFiles`:
   ```
   D:\home\LogFiles\
   ├── Application\
   │   └── logging-*.txt
   └── http\
       └── RawLogs\
   ```

### 3. Via Azure CLI

```bash
# Listar logs de aplicação
az webapp log tail --name fiap-techchallengefiap-fase2 --resource-group tech_challenge_fiap_2

# Baixar logs
az webapp log download --name fiap-techchallengefiap-fase2 --resource-group tech_challenge_fiap_2 --log-file logs.zip
```

### 4. Via PowerShell

```powershell
# Conectar ao Azure
Connect-AzAccount

# Obter logs em tempo real
Get-AzWebAppLog -ResourceGroupName "tech_challenge_fiap_2" -Name "fiap-techchallengefiap-fase2" -Tail
```

## 📂 Estrutura dos Logs

### Logs de Aplicação (Python)

Localização: `D:\home\LogFiles\Application\`

Formato dos logs (configurado em `api/main.py`):
```
%(asctime)s | %(levelname)s | %(name)s | %(message)s
```

Exemplo:
```
2025-01-19 12:30:45 | INFO | api | Iniciando treinamento via API...
2025-01-19 12:30:50 | INFO | api.services | Dataset carregado com 768 linhas
2025-01-19 12:35:20 | ERROR | api | Erro no treinamento: ...
```

### Logs HTTP

Localização: `D:\home\LogFiles\http\RawLogs\`

Contém:
- Requisições HTTP recebidas
- Status codes
- Tempo de resposta
- IPs de origem

## ⚙️ Configuração de Logging na Aplicação

### API (`api/main.py`)

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("api")
```

### Services (`api/services.py`)

```python
logger = logging.getLogger("api.services")
```

## 📊 Tipos de Logs Gerados

### 1. Logs de Treinamento
- Início/fim do treinamento
- Métricas dos modelos
- Tempo de execução
- Erros durante o processo

### 2. Logs de Avaliação
- Requisições de avaliação de pacientes
- Predições geradas
- Erros de validação

### 3. Logs HTTP
- Todas as requisições recebidas
- Status codes (200, 404, 500, etc.)
- Tempo de resposta

### 4. Logs de Erro
- Exceções não tratadas
- Stack traces completos
- Erros de conexão com Azure Storage

## 🔧 Habilitar/Desabilitar Logs

### Via Azure Portal

1. App Service → **App Service logs**
2. Configure:
   - **Application Logging (Filesystem)**: On/Off
   - **Level**: Error, Warning, Information, Verbose
   - **HTTP logging**: On/Off

### Via Terraform

Edite `infra/main.tf`:

```terraform
logs {
  application_logs {
    file_system_level = "Information"  # Error, Warning, Information, Verbose
  }
  http_logs {
    file_system {
      retention_in_days = 7
      retention_in_mb   = 35
    }
  }
}
```

Depois execute:
```bash
terraform plan
terraform apply
```

## 📈 Monitoramento Avançado (Opcional)

### Application Insights

Para logs mais detalhados e métricas avançadas, você pode configurar Application Insights:

1. No Azure Portal, vá em **Application Insights**
2. Crie um novo recurso
3. No App Service, vá em **Application Insights** → **Connect**
4. Selecione o recurso criado

Isso permite:
- Logs estruturados
- Métricas de performance
- Alertas automáticos
- Análise de dependências

## ⚠️ Limitações Atuais

- **Retenção**: 7 dias
- **Tamanho máximo**: 35MB por tipo de log
- **Nível**: Information (não captura logs Verbose/Debug)
- **Localização**: Apenas no sistema de arquivos (não em Blob Storage)

## 🚀 Melhorias Sugeridas

### 1. Logs em Blob Storage

Para logs de longo prazo, configure logs em Azure Blob Storage:

```terraform
logs {
  application_logs {
    azure_blob_storage {
      level             = "Information"
      retention_in_days = 30
      sas_url           = "https://..."
    }
  }
}
```

### 2. Application Insights

Adicione Application Insights para monitoramento completo:

```terraform
resource "azurerm_application_insights" "app" {
  name                = "app-insights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}
```

### 3. Logs Estruturados

Configure logging estruturado (JSON) na aplicação:

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        return json.dumps(log_entry)
```

## 📝 Comandos Úteis

### Ver logs em tempo real (local)
```bash
# Via Azure CLI
az webapp log tail --name fiap-techchallengefiap-fase2 --resource-group tech_challenge_fiap_2

# Via curl (se habilitado)
curl https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/logstream
```

### Baixar logs via Azure CLI
```bash
az webapp log download \
  --name fiap-techchallengefiap-fase2 \
  --resource-group tech_challenge_fiap_2 \
  --log-file logs.zip
```

## 🔗 Download Direto via URL (Kudu API)

### ⚠️ Autenticação Necessária

Todos os endpoints abaixo requerem autenticação **Basic Auth** usando as credenciais de publicação do App Service.

**Como obter as credenciais:**
1. Azure Portal → App Service → **Deployment Center** → **Get publish profile**
2. Abra o arquivo `.publishsettings` baixado
3. Use o `userName` e `userPWD` do arquivo XML

**Formato do username:** Geralmente `$<appname>` (ex: `$fiap-techchallengefiap-fase2`)

### 📥 Endpoints Disponíveis

#### 1. Download Completo de Todos os Logs (ZIP)

**URL:**
```
https://<app-name>.scm.azurewebsites.net/api/dump
```

**Exemplo para API:**
```bash
curl -u "$USERNAME:$PASSWORD" \
     https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/dump \
     -o all-logs.zip
```

**Exemplo para Frontend:**
```bash
curl -u "$USERNAME:$PASSWORD" \
     https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net/api/dump \
     -o frontend-logs.zip
```

**O que inclui:**
- Logs de aplicação (Python)
- Logs HTTP
- Logs de deployment
- Logs do sistema

#### 2. Download de Logs Específicos via VFS

**Estrutura da URL:**
```
https://<app-name>.scm.azurewebsites.net/api/vfs/LogFiles/{caminho}
```

**Exemplos:**

**Listar arquivos de log:**
```bash
curl -u "$USERNAME:$PASSWORD" \
     https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/vfs/LogFiles/
```

**Download de log de aplicação específico:**
```bash
curl -u "$USERNAME:$PASSWORD" \
     https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/vfs/LogFiles/Application/logging-20250119-123045.txt \
     -o app-log.txt
```

**Download de logs HTTP:**
```bash
curl -u "$USERNAME:$PASSWORD" \
     https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/vfs/LogFiles/http/RawLogs/ \
     -o http-logs.zip
```

#### 3. Download via PowerShell

```powershell
# Credenciais
$username = "$fiap-techchallengefiap-fase2"
$password = "sua-senha-aqui"
$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${username}:${password}"))

# Download completo
Invoke-WebRequest `
    -Uri "https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/dump" `
    -Headers @{Authorization=("Basic {0}" -f $base64AuthInfo)} `
    -OutFile "logs.zip"
```

#### 4. Download via Python

```python
import requests
import base64

# Credenciais
username = "$fiap-techchallengefiap-fase2"
password = "sua-senha-aqui"

# Autenticação Basic Auth
auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()

# Download completo
url = "https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/dump"
headers = {"Authorization": f"Basic {auth_string}"}

response = requests.get(url, headers=headers, stream=True)
with open("logs.zip", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Logs baixados com sucesso!")
```

#### 5. Download de Log Específico (Python)

```python
import requests
import base64
from datetime import datetime

username = "$fiap-techchallengefiap-fase2"
password = "sua-senha-aqui"
auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()

# Listar arquivos disponíveis
base_url = "https://fiap-techchallengefiap-fase2.scm.azurewebsites.net"
headers = {"Authorization": f"Basic {auth_string}"}

# Listar logs de aplicação
response = requests.get(f"{base_url}/api/vfs/LogFiles/Application/", headers=headers)
print("Arquivos disponíveis:", response.json())

# Download de arquivo específico
log_file = "logging-20250119-123045.txt"
response = requests.get(
    f"{base_url}/api/vfs/LogFiles/Application/{log_file}",
    headers=headers
)
with open(log_file, "wb") as f:
    f.write(response.content)
```

### 🔐 Usando Token de Autenticação (Alternativa)

Se preferir usar token em vez de senha:

1. Gere um token via Azure CLI:
```bash
az webapp deployment list-publishing-profiles \
  --name fiap-techchallengefiap-fase2 \
  --resource-group tech_challenge_fiap_2 \
  --xml
```

2. Use o token no lugar da senha:
```bash
curl -u "$USERNAME:$TOKEN" \
     https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/dump \
     -o logs.zip
```

### 📋 URLs Diretas para Seus App Services

**API:**
- Base URL: `https://fiap-techchallengefiap-fase2.scm.azurewebsites.net`
- Download completo: `https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/dump`
- Logs de aplicação: `https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/vfs/LogFiles/Application/`
- Logs HTTP: `https://fiap-techchallengefiap-fase2.scm.azurewebsites.net/api/vfs/LogFiles/http/`

**Frontend:**
- Base URL: `https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net`
- Download completo: `https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net/api/dump`
- Logs de aplicação: `https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net/api/vfs/LogFiles/Application/`
- Logs HTTP: `https://fiap-techchallengefiap-fase2-front.scm.azurewebsites.net/api/vfs/LogFiles/http/`

### ⚠️ Observações Importantes

1. **Autenticação obrigatória**: Todas as URLs requerem Basic Auth
2. **Credenciais sensíveis**: Nunca compartilhe as credenciais de publicação
3. **Retenção**: Logs são mantidos por 7 dias (conforme configurado)
4. **Tamanho**: Logs podem ser grandes, use `stream=True` em Python para downloads grandes
5. **Rate limiting**: Evite fazer muitas requisições em sequência

### 🛠️ Script Pronto para Download

Crie um arquivo `download_logs.py`:

```python
#!/usr/bin/env python3
"""
Script para baixar logs do Azure App Service via Kudu API
"""
import requests
import base64
import sys
from pathlib import Path

def download_logs(app_name, username, password, output_file="logs.zip"):
    """Baixa todos os logs do App Service."""
    base_url = f"https://{app_name}.scm.azurewebsites.net"
    dump_url = f"{base_url}/api/dump"
    
    # Autenticação
    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_string}"}
    
    print(f"Baixando logs de {app_name}...")
    
    try:
        response = requests.get(dump_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Logs salvos em: {output_file}")
        print(f"   Tamanho: {Path(output_file).stat().st_size / 1024 / 1024:.2f} MB")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao baixar logs: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python download_logs.py <app-name> <username> <password> [output-file]")
        print("\nExemplo:")
        print("  python download_logs.py fiap-techchallengefiap-fase2 '$fiap-techchallengefiap-fase2' 'senha' logs-api.zip")
        sys.exit(1)
    
    app_name = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    output_file = sys.argv[4] if len(sys.argv) > 4 else "logs.zip"
    
    download_logs(app_name, username, password, output_file)
```

**Uso:**
```bash
python download_logs.py fiap-techchallengefiap-fase2 '$fiap-techchallengefiap-fase2' 'sua-senha' logs-api.zip
```

## 🔗 Links Úteis

- [Azure App Service Logs Documentation](https://docs.microsoft.com/azure/app-service/troubleshoot-diagnostic-logs)
- [Kudu Documentation](https://github.com/projectkudu/kudu/wiki)
- [Azure CLI - Web App Logs](https://docs.microsoft.com/cli/azure/webapp/log)

---

**Última atualização**: Baseado na configuração atual em `infra/main.tf`
