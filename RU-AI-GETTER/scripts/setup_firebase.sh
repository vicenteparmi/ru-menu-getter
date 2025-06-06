#!/bin/bash
# Script de configuração para o sistema de upload de cardápios

echo "🔧 Configurando sistema de upload de cardápios dos RUs..."

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3 primeiro."
    exit 1
fi

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 não encontrado. Instale pip primeiro."
    exit 1
fi

# Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip3 install requests python-dotenv

# Verificar se arquivo .env existe
if [ ! -f ".env" ]; then
    echo "📄 Criando arquivo .env..."
    cp .env.example .env
    echo "✅ Arquivo .env criado. Configure suas credenciais Firebase antes de usar."
    echo ""
    echo "📝 Para configurar:"
    echo "   1. Abra o arquivo .env"
    echo "   2. Preencha BASE_URL com a URL do seu Firebase"
    echo "   3. Preencha FIREBASE_KEY com sua chave do Firebase"
    echo ""
    echo "🔍 Como obter as credenciais:"
    echo "   1. Acesse o Console do Firebase (https://console.firebase.google.com)"
    echo "   2. Selecione seu projeto"
    echo "   3. Vá em Configurações > Contas de Serviço"
    echo "   4. Copie a URL do banco de dados e a chave secreta"
else
    echo "✅ Arquivo .env já existe."
fi

# Verificar estrutura de diretórios
if [ ! -d "jsons" ]; then
    echo "📁 Criando diretório jsons/..."
    mkdir -p jsons
fi

if [ ! -d "core" ]; then
    echo "📁 Criando diretório core/..."
    mkdir -p core
fi

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "🚀 Para usar o sistema:"
echo "   1. Execute: python3 main.py (para coletar cardápios)"
echo "   2. Execute: python3 interface/menu_review_gui.py (para revisar e fazer upload)"
echo ""
echo "📚 Documentação adicional em README.md"
