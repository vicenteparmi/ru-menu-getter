# UTFPR Menu Scraper

Sistema automatizado para processar cardápios da UTFPR a partir de PDFs no Google Drive.

## Otimizações 2026

- ✅ **Economia de API**: Extração de texto local (pdfplumber) antes de enviar ao Gemini (~97% de economia em PDFs de texto).
- ✅ **Saída Estruturada**: Uso de Pydantic para garantir JSON 100% válido para o Firebase.
- ✅ **Ano Dinâmico**: Datas tratadas dinamicamente com base no ano atual.
- ✅ **Filtro de Ruído**: Redução do `thinking_budget` para 2100 para menor latência e custo.

## Funcionalidades

- ✅ Baixa PDFs automaticamente de pasta pública do Google Drive
- ✅ Processa PDFs usando Google Gemini AI (Texto-primeiro -> Inline -> File API)
- ✅ Valida e estrutura dados com Pydantic
- ✅ Envia automaticamente para Firebase

## Requisitos

- Python 3.11+
- Google Gemini API Key
- Firebase credentials (BASE_URL e FIREBASE_KEY)
- Google Service Account JSON (para acessar Google Drive)

## Configuração Local

1. Instalar dependências:
```bash
pip install -r requirements.txt
```

2. Configurar variáveis de ambiente (`.env`):
```
GEMINI_API_KEY=sua_chave_aqui
BASE_URL=https://seu-firebase.firebaseio.com
FIREBASE_KEY=sua_chave_firebase
```

3. Executar:
```bash
python main.py
```

## Deploy no Google Cloud Run (Job)

O sistema está configurado para rodar como um **Cloud Run Job**.

### Como atualizar o container:

Basta rodar o comando abaixo na pasta raiz:

```bash
gcloud run jobs deploy utfpr-menu-scraper \
  --source . \
  --region southamerica-east1
```

Este comando irá zipar o código (respeitando o `.gcloudignore`), buildar a imagem no Cloud Build e atualizar o Job.

### Como atualizar a chave de API expirada:

Se a execução falhar por "API key expired", atualize as variáveis de ambiente do Job:

```bash
gcloud run jobs update utfpr-menu-scraper \
  --region southamerica-east1 \
  --set-env-vars="GEMINI_API_KEY=SUA_NOVA_CHAVE"
```

## Estrutura do Projeto

```
UTFPR/
├── main.py                    # Script principal (orquestração)
├── gemini_pdf_processor.py    # Integração Gemini (estratégia de extração)
├── models.py                  # Modelos Pydantic e validação de schema
├── pdf_text_extractor.py      # Extração local de texto e tabelas
├── google_drive_downloader.py # Download de PDFs do Google Drive
├── utfpr_firebase_uploader.py # Upload de dados para Firebase
├── Dockerfile                 # Configuração do container
├── .gcloudignore              # Arquivos ignorados no deploy (importante!)
└── requirements.txt           # Dependências Python
```

## Troubleshooting

### "API key expired"
O Cloud Run Job usa uma variável de ambiente. Veja a seção de deploy acima para saber como atualizar sem precisar de um novo deploy de código.

### "Texto extraído muito curto"
Isso indica que o PDF é baseado em imagem (scan). O sistema detecta isso automaticamente e envia o arquivo completo para o Gemini processar via visão computacional.

### "Erro ao processar PDF inline"
Certifique-se de que a biblioteca `google-genai` está instalada e que o modelo usado suporta o formato enviado.

