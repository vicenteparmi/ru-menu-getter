#!/bin/zsh
# Script de inicialização do projeto RUMCP

# Funções de cor para terminal
c_reset='\033[0m'
c_green='\033[1;32m'
c_yellow='\033[1;33m'
c_blue='\033[1;34m'
c_magenta='\033[1;35m'
c_red='\033[1;31m'

# Nome do ambiente virtual
env_name=".venv"

# Cria o ambiente virtual se não existir
if [ ! -d "$env_name" ]; then
    echo "${c_blue}Criando ambiente virtual...${c_reset}"
    python3 -m venv $env_name
fi

# Ativa o ambiente virtual
echo "${c_blue}Ativando ambiente virtual...${c_reset}"
source $env_name/bin/activate

# Instala os pacotes necessários
echo "${c_blue}Instalando dependências do requirements.txt...${c_reset}"
pip install --upgrade pip
pip install -r requirements.txt

# Instala dependências extras sempre necessárias
for pkg in google-generativeai python-dotenv colorama; do
    echo "${c_blue}Instalando $pkg...${c_reset}"
    pip install --upgrade $pkg
    done

# Exporta as variáveis do .env para o ambiente
if [ -f .env ]; then
    echo "${c_blue}Carregando variáveis de ambiente do .env...${c_reset}"
    export $(grep -v '^#' .env | xargs)
fi

echo "${c_green}Ambiente pronto!${c_reset}"

echo "${c_magenta}Executando o script principal (main.py)...${c_reset}"
python3 main.py
