#!/usr/bin/env python3
"""
Google Drive Downloader - Baixa PDFs de uma pasta pública do Google Drive
"""

import os
import re
import requests
import io
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

# Google Drive API
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import google.auth
    from google.oauth2 import service_account
    HAVE_GDRIVE = True
except Exception as e:
    print(f"[AVISO] Não foi possível importar bibliotecas Google: {e}")
    HAVE_GDRIVE = False


def extract_folder_id(drive_url: str) -> str:
    """
    Extrai o ID da pasta do Google Drive da URL.
    
    Args:
        drive_url: URL da pasta do Google Drive
        
    Returns:
        ID da pasta
    """
    # Padrão: https://drive.google.com/drive/folders/ID
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', drive_url)
    if match:
        return match.group(1)
    
    # Tentar extrair de query params
    parsed = urlparse(drive_url)
    params = parse_qs(parsed.query)
    if 'id' in params:
        return params['id'][0]
    
    raise ValueError(f"Não foi possível extrair ID da pasta de: {drive_url}")


def get_drive_service():
    """
    Cria e retorna um serviço Drive autenticado.
    Retorna None se não for possível autenticar.
    """
    if not HAVE_GDRIVE:
        return None
    
    try:
        sa_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('GDRIVE_SERVICE_ACCOUNT_FILE')
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        if sa_path and os.path.exists(sa_path):
            print(f"[INFO] Usando service account: {sa_path}")
            creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
            return build('drive', 'v3', credentials=creds, cache_discovery=False)
        else:
            raise ValueError(f"Service account não encontrado em: {sa_path}")
    except Exception as e:
        print(f"[AVISO] Não foi possível inicializar serviço Drive: {e}")
        return None


def list_files_in_folder(folder_id: str, drive_service=None) -> tuple:
    """
    Lista arquivos em uma pasta pública do Google Drive.
    
    Args:
        folder_id: ID da pasta do Google Drive
        drive_service: Serviço Drive já inicializado (opcional)
        
    Returns:
        Tuple (lista de arquivos, serviço Drive usado)
    """
    # Preferir usar a Google Drive API com credenciais (ADC ou service account)
    if HAVE_GDRIVE:
        try:
            service = drive_service or get_drive_service()
            if service is None:
                raise ValueError("Não foi possível obter serviço Drive")

            files = []
            page_token = None
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            print(f"[INFO] Listando PDFs na pasta: {folder_id}")
            while True:
                resp = service.files().list(q=query, fields='nextPageToken, files(id, name, mimeType, size)', pageToken=page_token, pageSize=1000).execute()
                files.extend(resp.get('files', []))
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"[OK] Encontrados {len(files)} arquivos via Drive API")
            return files, service
        except Exception as e:
            print(f"[ERRO] Falha ao listar via Drive API: {e}")
            print("[INFO] Tentando método alternativo (API Key / scraping)...")

    # Fallback: usar API pública com key ou scraping
    api_url = f"https://www.googleapis.com/drive/v3/files"
    params = {
        'q': f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
        'fields': 'files(id, name, mimeType, size)',
        'key': os.environ.get('GOOGLE_API_KEY', '')
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('files', []), None
    except Exception as e:
        print(f"[ERRO] Falha ao listar arquivos: {e}")
        print("[INFO] Tentando método alternativo (scraping)...")
        return list_files_scraping(folder_id), None


def list_files_scraping(folder_id: str) -> List[dict]:
    """
    Lista arquivos fazendo scraping da página pública do Google Drive.
    Método alternativo quando a API não está disponível.
    """
    # URL da visualização pública
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        response = requests.get(folder_url)
        response.raise_for_status()
        
        # Procurar por IDs de arquivos no HTML
        # Padrão: "id":"FILE_ID"
        file_ids = re.findall(r'"id":"([a-zA-Z0-9_-]+)"', response.text)
        
        # Procurar por nomes de arquivos PDF
        pdf_names = re.findall(r'"title":"([^"]*\.pdf)"', response.text)
        
        files = []
        for file_id, name in zip(file_ids, pdf_names):
            files.append({
                'id': file_id,
                'name': name,
                'mimeType': 'application/pdf'
            })
        
        return files
    except Exception as e:
        print(f"[ERRO] Falha no scraping: {e}")
        return []


def download_file(file_id: str, dest_path: str, drive_service: Optional[object] = None) -> bool:
    """
    Baixa um arquivo do Google Drive.
    
    Args:
        file_id: ID do arquivo no Google Drive
        dest_path: Caminho de destino para salvar o arquivo
        
    Returns:
        True se o download foi bem-sucedido
    """
    # URL de download direto
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        if drive_service is not None and HAVE_GDRIVE:
            # Usar MediaIoBaseDownload
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(dest_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
            return True
        else:
            session = requests.Session()
            response = session.get(download_url, stream=True)
            # Verificar se precisa confirmar (arquivos grandes)
            if 'confirm=' in response.text:
                confirm_token = re.search(r'confirm=([0-9A-Za-z_]+)', response.text)
                if confirm_token:
                    download_url = f"{download_url}&confirm={confirm_token.group(1)}"
                    response = session.get(download_url, stream=True)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"[ERRO] Falha ao baixar arquivo {file_id}: {e}")
        return False


def download_pdfs_from_folder(drive_url: str, dest_dir: str) -> List[str]:
    """
    Baixa todos os PDFs de uma pasta do Google Drive.
    
    Args:
        drive_url: URL da pasta do Google Drive
        dest_dir: Diretório de destino para salvar os PDFs
        
    Returns:
        Lista de caminhos dos arquivos baixados
    """
    print(f"[INFO] Extraindo ID da pasta...")
    folder_id = extract_folder_id(drive_url)
    print(f"[INFO] ID da pasta: {folder_id}")
    
    print(f"[INFO] Listando arquivos...")
    files, drive_service = list_files_in_folder(folder_id)
    
    if not files:
        print("[AVISO] Nenhum arquivo encontrado")
        return []
    
    print(f"[INFO] Encontrados {len(files)} arquivos")
    
    # Criar diretório de destino se não existir
    os.makedirs(dest_dir, exist_ok=True)
    
    downloaded_files = []
    
    for file_info in files:
        file_id = file_info['id']
        file_name = file_info['name']
        dest_path = os.path.join(dest_dir, file_name)
        
        print(f"[INFO] Baixando: {file_name}")
        
        if download_file(file_id, dest_path, drive_service):
            print(f"[OK] Salvo em: {dest_path}")
            downloaded_files.append(dest_path)
        else:
            print(f"[ERRO] Falha ao baixar: {file_name}")
    
    return downloaded_files


if __name__ == "__main__":
    # Teste
    test_url = "https://drive.google.com/drive/folders/10GEyvT-ma0iOGz-ale1CpdPM5Lt2fdhQ"
    test_dir = "/tmp/utfpr_test"
    
    files = download_pdfs_from_folder(test_url, test_dir)
    print(f"\n[RESULTADO] Baixados {len(files)} arquivos")

