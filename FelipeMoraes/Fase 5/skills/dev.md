---
name: dev
description: Sobe o ambiente de desenvolvimento completo (backend FastAPI + frontend)
---

# Skill: Ambiente de Desenvolvimento

Ao executar esta skill, siga exatamente os passos abaixo:

## 1. Verificar pré-requisitos

```bash
python --version   # precisa ser 3.11+
```

Se não tiver Python 3.11+, informe o usuário e pare.

## 2. Verificar .env

Verifique se o arquivo `.env` existe na raiz do projeto (`Fase 5/.env`).
- Se não existir, copie de `.env.example` e informe o usuário para configurar as chaves.
- Se existir, leia `LLM_PROVIDER` para informar qual provider está ativo.

## 3. Instalar dependências do backend

```bash
cd backend
pip install -r requirements.txt
```

Se falhar, mostre o erro e pare.

## 4. Subir o backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Execute em background. Aguarde 2 segundos e verifique se está respondendo:
```bash
curl http://localhost:8000/api/health
```

Se retornar JSON com `"status": "ok"`, o backend está no ar.

## 5. Instruções para o frontend

Informe o usuário:

> **Frontend:** Abra um novo terminal na pasta `Fase 5/` e execute:
> ```bash
> python -m http.server 3000 --directory frontend
> ```
> Depois acesse: **http://localhost:3000**

## 6. Resumo do que está rodando

Exiba ao usuário:
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000 (quando iniciado)
- Provider LLM ativo: `{valor do LLM_PROVIDER no .env}`

## Troubleshooting

**Porta 8000 em uso:**
```bash
uvicorn main:app --reload --port 8001
```
Atualizar `API_BASE` em `frontend/js/app.js` para `http://localhost:8001`.

**Erro de API key (OpenAI):**
Verificar `OPENAI_API_KEY` no `.env`.

**Ollama/LM Studio offline:**
O sistema continua funcionando — apenas aquele provider ficará marcado como "(offline)" no frontend.
