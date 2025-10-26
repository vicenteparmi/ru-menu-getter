#!/bin/bash
# Script de execução para UTFPR Menu Scraper
# Funciona no macOS e Linux

set -e  # Parar em caso de erro

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}UTFPR Menu Scraper${NC}"
echo -e "${GREEN}================================${NC}"

# Verificar se estamos na pasta correta
if [ ! -f "main.py" ]; then
    echo -e "${RED}Erro: Execute este script da pasta UTFPR${NC}"
    exit 1
fi

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Aviso: Arquivo .env não encontrado${NC}"
    echo -e "${YELLOW}Copiando .env.example para .env...${NC}"
    cp .env.example .env
    echo -e "${RED}Configure o arquivo .env com suas credenciais!${NC}"
    exit 1
fi

# Carregar variáveis de ambiente
export $(cat .env | grep -v '^#' | xargs)

# Verificar dependências
echo -e "${YELLOW}Verificando dependências Python...${NC}"
if ! python3 -c "import google.generativeai, requests, dotenv" 2>/dev/null; then
    echo -e "${YELLOW}Instalando dependências...${NC}"
    pip3 install -r requirements.txt
fi

# Executar programa
echo -e "${GREEN}Iniciando processamento...${NC}"
python3 main.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Processamento concluído com sucesso!${NC}"
else
    echo -e "${RED}❌ Erro no processamento (código: $exit_code)${NC}"
fi

exit $exit_code
