# 🍽️ Interface de Revisão de Cardápios dos RUs

Esta interface permite revisar, aprovar, excluir ou regenerar os cardápios dos Restaurantes Universitários após a validação dos JSONs.

## ✨ Funcionalidades

### 📋 Visão Geral
- Lista todos os arquivos JSON de cardápios disponíveis
- Exibe informações básicas sobre cada arquivo
- Status em tempo real das operações

### 📄 Visualização Detalhada
- Visualização formatada e organizada dos cardápios
- Informações do arquivo (nome, tamanho, data de modificação)
- Estatísticas do cardápio (dias totais, dias com refeições, total de pratos)
- Validação estrutural automática com relatório de problemas

### 🎛️ Ações Disponíveis

#### ✅ Aprovar Cardápio
- Marca o cardápio como aprovado
- Adiciona timestamp de aprovação
- Salva as alterações no arquivo JSON

#### 🗑️ Excluir Cardápio
- Remove completamente o arquivo JSON
- **Ação irreversível** - use com cuidado!

#### 🔄 Obter Novamente
- Executa novamente o scraper para regenerar o cardápio
- Substitui o arquivo atual pelos dados mais recentes
- Útil quando há atualizações no site do RU

#### 🔍 Validar Todos
- Executa validação completa de todos os arquivos JSON
- Verifica estrutura, formato de datas e integridade dos dados

## 🚀 Como Usar

### Método 1: Script Automático
```bash
./start_review_gui.sh
```

### Método 2: Manual
```bash
# Ativar ambiente virtual (se existir)
source venv/bin/activate

# Instalar dependências
pip install flask

# Executar interface
python3 menu_review_web.py
```

### Método 3: Após Execução do Scraper Principal
A interface é aberta automaticamente após a execução do `main.py` e validação dos JSONs.

## 🌐 Acesso

A interface estará disponível em:
- **URL Principal**: http://localhost:8080
- **URLs Alternativas**: http://localhost:8081 ou http://localhost:8082 (se a porta 8080 estiver ocupada)

## 📱 Interface

### Página Principal
- **Cartões de Arquivo**: Cada cardápio é exibido como um cartão clicável
- **Botões de Ação Global**: Validar todos os arquivos, atualizar lista
- **Status Bar**: Mostra o status atual das operações
- **Atualização Automática**: Status atualizado a cada 3 segundos

### Página de Visualização
- **Painel Lateral**: Informações do arquivo, estatísticas e validação
- **Conteúdo Principal**: Cardápio formatado por dias e refeições
- **Botões de Ação**: Aprovar, excluir ou regenerar o cardápio específico

## 🎨 Design

- **Interface Responsiva**: Funciona em desktop, tablet e mobile
- **Design Moderno**: Gradientes, sombras e animações suaves
- **Iconografia Clara**: Emojis e ícones para facilitar a navegação
- **Cores Intuitivas**: Verde para aprovação, vermelho para exclusão, amarelo para atenção

## ⚠️ Importantes

1. **Backup**: Sempre mantenha backup dos arquivos JSON antes de fazer alterações
2. **Validação**: Use a função "Validar Todos" regularmente para garantir integridade
3. **Regeneração**: A regeneração substitui completamente o arquivo atual
4. **Exclusão**: A exclusão é irreversível - confirme antes de executar

## 🐛 Solução de Problemas

### Porta em Uso
Se a porta 8080 estiver ocupada:
1. O script automaticamente tentará portas 8081 e 8082
2. Ou desative o AirPlay Receiver do macOS (Sistema > Geral > AirDrop e Handoff)

### Flask Não Encontrado
```bash
pip install flask
```

### Problemas de Permissão
```bash
chmod +x start_review_gui.sh
```

### Ambiente Virtual
Se houver problemas com dependências:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📊 Formato dos Dados

A interface trabalha com arquivos JSON no formato:
```json
{
  "YYYY-MM-DD": {
    "menu": [
      ["café da manhã items..."],
      ["almoço items..."], 
      ["jantar items..."]
    ],
    "weekday": "Nome do Dia",
    "timestamp": 0,
    "approved": true,
    "approved_timestamp": 1234567890
  }
}
```

## 🔄 Integração

Esta interface integra-se com:
- **main.py**: Scraper principal dos RUs
- **json_validator.py**: Validação estrutural dos JSONs
- **scrapers/**: Módulos de coleta de dados específicos por RU

---

**Desenvolvido para facilitar a gestão e aprovação dos cardápios dos Restaurantes Universitários** 🎓
