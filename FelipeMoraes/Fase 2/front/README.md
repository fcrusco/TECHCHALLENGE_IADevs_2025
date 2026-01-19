# Frontend - Avaliação de Risco de Diabetes

Interface web simples e limpa para consumir as APIs de avaliação e treinamento de modelos de diabetes.

## Estrutura

- `index.html` - Página principal com interface de avaliação e treinamento
- `style.css` - Estilos CSS com design limpo e cores neutras
- `app.js` - JavaScript para consumir as APIs
- `server.py` - Servidor Flask simples para servir os arquivos estáticos

## Como executar localmente

```bash
pip install flask
python server.py
```

Acesse: http://localhost:5000

## Variáveis de Ambiente

O frontend tenta detectar automaticamente a URL da API. Se necessário, edite a constante `API_BASE_URL` no arquivo `app.js`.
