#!/bin/bash
# Script para fazer upload dos cardápios UFSC para Firebase
# Uso: ./scripts/upload_ufsc_firebase.sh

cd "$(dirname "$0")/.."

echo "🔥 Upload UFSC para Firebase"
echo "================================"

# Verificar se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Execute primeiro:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado."
    echo "   Copie o arquivo .env.example para .env e configure suas credenciais Firebase:"
    echo "   cp .env.example .env"
    echo "   # Edite o .env com suas credenciais"
    exit 1
fi

# Ativar ambiente virtual e executar upload
echo "🚀 Ativando ambiente virtual e iniciando upload..."
source .venv/bin/activate

echo ""
echo "Escolha uma opção:"
echo "1) Upload rápido (apenas aprovados)"
echo "2) Teste completo com diagnósticos"
echo "3) Testar apenas conexão Firebase"
echo ""
read -p "Digite sua escolha (1-3): " choice

case $choice in
    1)
        echo "📤 Fazendo upload rápido..."
        python core/firebase_uploader.py
        ;;
    2)
        echo "🔍 Executando teste completo..."
        python test_ufsc_upload.py
        ;;
    3)
        echo "🔗 Testando conexão..."
        python -c "
import sys
sys.path.append('core')
from firebase_uploader import test_firebase_connection
if test_firebase_connection():
    print('✅ Conexão com Firebase OK!')
else:
    print('❌ Falha na conexão com Firebase')
"
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

echo ""
echo "✨ Processo concluído!"
