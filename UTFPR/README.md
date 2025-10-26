# UTFPR Menu Scraper

Sistema automatizado para processar cardápios da UTFPR a partir de PDFs no Google Drive.

## Funcionalidades

- ✅ Baixa PDFs automaticamente de pasta pública do Google Drive
- ✅ Processa PDFs usando Google Gemini AI (sem necessidade de OCR)
- ✅ Valida e estrutura dados em JSON
- ✅ Envia automaticamente para Firebase
- ✅ Suporta arquivos de qualquer tamanho (inline para <20MB, File API para maiores)

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

2. Baixar credenciais do Firebase:
   - Acesse [Firebase Console](https://console.firebase.google.com/)
   - Selecione seu projeto (campusdine-menu)
   - Vá em Configurações do Projeto > Contas de Serviço
   - Clique em "Gerar nova chave privada"
   - Baixe o arquivo JSON e salve como `firebase-service-account.json` na pasta UTFPR

3. Configurar variáveis de ambiente (.env):
```
GEMINI_API_KEY=sua_chave_aqui
BASE_URL=https://seu-firebase.firebaseio.com
FIREBASE_KEY=sua_chave_firebase
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json
```

4. Executar:
```bash
python main.py
```

## Deploy no Google Cloud Run

### Build e Push da imagem:

```bash
# Build para arquitetura amd64
docker build --platform linux/amd64 -t gcr.io/campusdine-menu/utfpr-menu-scraper:latest .

# Push para GCR
docker push gcr.io/campusdine-menu/utfpr-menu-scraper:latest
```

### Deploy como Cloud Run Job:

```bash
gcloud run jobs deploy utfpr-menu-scraper \
  --image gcr.io/campusdine-menu/utfpr-menu-scraper:latest \
  --region southamerica-east1 \
  --max-retries 1 \
  --memory 1Gi \
  --cpu 1 \
  --task-timeout 20m \
  --set-env-vars GEMINI_API_KEY=sua_chave,BASE_URL=sua_url,FIREBASE_KEY=sua_chave
```

### Agendar execuções:

```bash
# Segunda às 8h
gcloud scheduler jobs create http utfpr-scraper-segunda-8h \
  --location southamerica-east1 \
  --schedule="0 8 * * 1" \
  --time-zone="America/Sao_Paulo" \
  --uri="https://southamerica-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/campusdine-menu/jobs/utfpr-menu-scraper:run" \
  --http-method POST \
  --oauth-service-account-email=1081471577742-compute@developer.gserviceaccount.com
```

## Estrutura do Projeto

```
UTFPR/
├── main.py                      # Script principal
├── google_drive_downloader.py   # Download de PDFs do Google Drive
├── gemini_pdf_processor.py      # Processamento com Gemini AI
├── requirements.txt             # Dependências Python
├── Dockerfile                   # Container Docker
└── README.md                    # Este arquivo
```

## Como Funciona

1. **Download**: Acessa pasta pública do Google Drive e baixa todos os PDFs
2. **Processamento**: Cada PDF é enviado para Gemini AI que extrai o cardápio estruturado
3. **Validação**: JSON é validado e corrigido automaticamente se necessário
4. **Upload**: Dados são enviados para Firebase seguindo estrutura padrão

## URL do Google Drive

Pasta atual: https://drive.google.com/drive/folders/10GEyvT-ma0iOGz-ale1CpdPM5Lt2fdhQ

Para alterar, edite a constante `DRIVE_FOLDER_URL` em `main.py`.

## Logs

O sistema gera logs coloridos detalhados de cada etapa:
- 🔵 INFO: Informações gerais
- 🟢 SUCCESS: Operações bem-sucedidas
- 🟡 WARNING: Avisos
- 🔴 ERROR: Erros

## Troubleshooting

### "GEMINI_API_KEY não definida"
Configure a variável de ambiente com sua chave da API Gemini.

### "Nenhum PDF encontrado no Google Drive"
Verifique se a pasta está pública e a URL está correta.

### "Falha ao validar JSON"
O sistema tenta corrigir automaticamente. Se persistir, verifique o formato do PDF.
