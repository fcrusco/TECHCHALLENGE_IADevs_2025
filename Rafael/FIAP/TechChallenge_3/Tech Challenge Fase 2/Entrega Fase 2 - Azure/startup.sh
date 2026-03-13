#!/bin/bash
echo "=== Instalando dependencias ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "=== Iniciando API FastAPI ==="
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000