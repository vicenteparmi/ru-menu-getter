#!/bin/bash

# Script para iniciar a interface de revisão de cardápios dos RUs

echo "🍽️  Iniciando Interface de Revisão de Cardápios dos RUs"
echo "=================================================="

# Verificar se está no diretório correto
if [ ! -f "menu_review_web.py" ]; then
    echo "❌ Erro: Execute este script no diretório do projeto RUMCP"
    exit 1
fi

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    echo "🔧 Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Verificar se Flask está instalado
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Instalando Flask..."
    pip3 install flask
fi

# Verificar porta disponível
PORT=8080
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Porta $PORT em uso, tentando porta 8081..."
    PORT=8081
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Porta $PORT em uso, tentando porta 8082..."
        PORT=8082
    fi
fi

echo "🚀 Iniciando servidor na porta $PORT..."
echo "🌐 Acesse: http://localhost:$PORT"
echo ""
echo "Para parar o servidor, pressione Ctrl+C"
echo ""

# Substituir porta no arquivo se necessário
if [ $PORT -ne 8080 ]; then
    sed -i.bak "s/port=8080/port=$PORT/g" menu_review_web.py
fi

# Iniciar servidor
python3 menu_review_web.py

# Restaurar porta original se foi alterada
if [ $PORT -ne 8080 ] && [ -f "menu_review_web.py.bak" ]; then
    mv menu_review_web.py.bak menu_review_web.py
fi

echo ""
echo "✅ Servidor encerrado."
