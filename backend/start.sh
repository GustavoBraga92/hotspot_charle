#!/bin/bash
# Instala dependências e inicia o backend

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Arquivo .env criado. Edite-o com os dados do MikroTik antes de continuar."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

echo "Iniciando API na porta 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000
