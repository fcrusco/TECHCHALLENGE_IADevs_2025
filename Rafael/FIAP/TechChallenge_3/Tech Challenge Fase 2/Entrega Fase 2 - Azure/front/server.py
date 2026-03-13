"""
Servidor simples para servir o frontend estático.
"""
from flask import Flask, send_from_directory, send_file
import os

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    """Serve a página principal com URL da API injetada."""
    # Lê a URL da API da variável de ambiente ou usa padrão
    api_base_url = os.environ.get('API_BASE_URL', 'http://localhost:8000')
    
    # Lê o arquivo HTML
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Injeta a URL da API no meta tag e cria uma variável JavaScript global
    html = html.replace(
        'content="{{ API_BASE_URL }}"',
        f'content="{api_base_url}"'
    )
    
    # Adiciona script inline para definir a URL da API globalmente
    script_tag = f'<script>window.API_BASE_URL = "{api_base_url}";</script>'
    html = html.replace('</head>', f'    {script_tag}\n</head>')
    
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/<path:path>')
def serve_static(path):
    """Serve arquivos estáticos (CSS, JS)."""
    # Evita servir o server.py
    if path == 'server.py' or path.endswith('.py'):
        return "Not found", 404
    return send_from_directory('.', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
