#!/bin/bash
echo "=== Instalando dependencias ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "=== Iniciando aplicacao ==="
python src/treinamento.py