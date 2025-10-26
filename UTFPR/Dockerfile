# Usa uma imagem oficial Python
FROM python:3.11-slim

# Define a pasta de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache de layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY main.py .
COPY google_drive_downloader.py .
COPY gemini_pdf_processor.py .
COPY utfpr_firebase_uploader.py .

# Copiar service account JSON
COPY campusdine-menu-6d4386666d2c.json .

# Variáveis de ambiente (serão configuradas no Cloud Run)
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=campusdine-menu-6d4386666d2c.json

# Comando para rodar o script
CMD ["python", "main.py"]
