#!/usr/bin/env python3
"""
Script para baixar logs do Azure App Service via Kudu API

Uso:
    python download_logs.py <app-name> <username> <password> [output-file]

Exemplo:
    python download_logs.py fiap-techchallengefiap-fase2 '$fiap-techchallengefiap-fase2' 'senha' logs-api.zip
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
    
    print(f"🔄 Baixando logs de {app_name}...")
    print(f"   URL: {dump_url}")
    
    try:
        response = requests.get(dump_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r   Progresso: {percent:.1f}% ({downloaded / 1024 / 1024:.2f} MB)", end="")
        
        print()  # Nova linha após progresso
        file_size = Path(output_file).stat().st_size / 1024 / 1024
        print(f"✅ Logs salvos em: {output_file}")
        print(f"   Tamanho: {file_size:.2f} MB")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao baixar logs: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Resposta: {e.response.text[:200]}")
        return False

def list_log_files(app_name, username, password, log_type="Application"):
    """Lista arquivos de log disponíveis."""
    base_url = f"https://{app_name}.scm.azurewebsites.net"
    vfs_url = f"{base_url}/api/vfs/LogFiles/{log_type}/"
    
    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_string}"}
    
    try:
        response = requests.get(vfs_url, headers=headers)
        response.raise_for_status()
        
        files = response.json()
        print(f"\n📁 Arquivos de log disponíveis ({log_type}):")
        for file_info in files:
            if isinstance(file_info, dict):
                name = file_info.get('name', 'N/A')
                size = file_info.get('size', 0)
                mtime = file_info.get('mtime', 'N/A')
                print(f"   - {name} ({size / 1024:.2f} KB) - {mtime}")
        
        return files
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("=" * 60)
        print("Download de Logs do Azure App Service")
        print("=" * 60)
        print("\nUso:")
        print("  python download_logs.py <app-name> <username> <password> [output-file]")
        print("\nParâmetros:")
        print("  app-name    : Nome do App Service (ex: fiap-techchallengefiap-fase2)")
        print("  username    : Username de publicação (ex: $fiap-techchallengefiap-fase2)")
        print("  password    : Senha de publicação")
        print("  output-file : Nome do arquivo de saída (opcional, padrão: logs.zip)")
        print("\nExemplos:")
        print("  # API")
        print("  python download_logs.py fiap-techchallengefiap-fase2 '$fiap-techchallengefiap-fase2' 'senha' logs-api.zip")
        print("\n  # Frontend")
        print("  python download_logs.py fiap-techchallengefiap-fase2-front '$fiap-techchallengefiap-fase2-front' 'senha' logs-frontend.zip")
        print("\n  # Listar arquivos disponíveis")
        print("  python download_logs.py fiap-techchallengefiap-fase2 '$fiap-techchallengefiap-fase2' 'senha' --list")
        print("\n💡 Dica: Obtenha as credenciais em:")
        print("   Azure Portal → App Service → Deployment Center → Get publish profile")
        sys.exit(1)
    
    app_name = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    # Modo listagem
    if len(sys.argv) > 4 and sys.argv[4] == "--list":
        print(f"📋 Listando logs de {app_name}...")
        list_log_files(app_name, username, password, "Application")
        list_log_files(app_name, username, password, "http")
    else:
        output_file = sys.argv[4] if len(sys.argv) > 4 else "logs.zip"
        download_logs(app_name, username, password, output_file)
