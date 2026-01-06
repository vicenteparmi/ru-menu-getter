#!/usr/bin/env python3
"""
UTFPR Menu Scraper - Processa cardápios do Google Drive
Baixa PDFs do Google Drive, processa com IA e envia para Firebase
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Funções de logging locais
def log_info(msg):
    print(f"[INFO] {msg}")

def log_success(msg):
    print(f"[SUCCESS] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")

from utfpr_firebase_uploader import upload_utfpr_menu_to_firebase
from google_drive_downloader import download_pdfs_from_folder
from gemini_pdf_processor import process_pdf_inline
from models import validate_menu_data


def process_pdf_menu(pdf_path: str) -> dict | None:
    """
    Processa um PDF de cardápio e retorna o JSON estruturado.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
    
    Returns:
        Dict com o cardápio processado
    """
    log_info(f"Processando PDF: {pdf_path}")
    
    try:
        log_info("Enviando para processamento (texto ou PDF)...")
        json_text = process_pdf_inline(pdf_path)
        
        # Parse JSON
        menu_json = json.loads(json_text)
        
    except Exception as e:
        log_error(f"Erro ao processar com Gemini: {e}")
        return None
    
    # Validar JSON usando Pydantic models
    log_info("Validando JSON com Pydantic...")
    is_valid, processed_json, errors = validate_menu_data(menu_json)
    
    if not is_valid:
        log_warning(f"JSON com problemas encontrados: {len(errors)}")
        for error in errors[:3]:
            log_warning(f"  - {error}")
    
    if processed_json:
        menu_json = processed_json
    
    log_success("JSON processado e validado com sucesso!")
    return menu_json


def main():
    """Função principal."""
    log_info("=" * 60)
    log_info("UTFPR Menu Scraper - Iniciando processamento")
    log_info("=" * 60)
    
    # Verificar variáveis de ambiente
    if not os.environ.get("BASE_URL") or not os.environ.get("FIREBASE_KEY"):
        log_warning("Variáveis de ambiente do Firebase não configuradas")
        log_warning("BASE_URL e FIREBASE_KEY devem estar definidas")
    
    # MODO TESTE: usar arquivo local se existir
    test_pdf = Path(__file__).parent / "test_menu.pdf"
    if test_pdf.exists():
        log_warning("MODO TESTE: Usando arquivo local test_menu.pdf")
        pdf_files = [str(test_pdf)]
    else:
        # URL do Google Drive
        DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/10GEyvT-ma0iOGz-ale1CpdPM5Lt2fdhQ"
        
        # Baixar PDFs do Google Drive
        log_info("Baixando PDFs do Google Drive...")
        temp_dir = tempfile.mkdtemp()
        log_info(f"Diretório temporário: {temp_dir}")
        
        pdf_files = download_pdfs_from_folder(DRIVE_FOLDER_URL, temp_dir)
        
        if not pdf_files:
            log_error("Nenhum PDF encontrado no Google Drive")
            return 1
        
        log_success(f"Baixados {len(pdf_files)} arquivos PDF")
    
    # Processar cada PDF
    total_processed = 0
    total_uploaded = 0
    
    for pdf_file in pdf_files:
        log_info(f"\n{'=' * 60}")
        log_info(f"Processando: {os.path.basename(pdf_file)}")
        log_info(f"{'=' * 60}")
        
        try:
            # Processar PDF
            menu_data = process_pdf_menu(pdf_file)
            
            if menu_data:
                total_processed += 1
                
                # Fazer upload para Firebase
                log_info("Enviando para Firebase...")
                success = upload_utfpr_menu_to_firebase(menu_data=menu_data)
                
                if success:
                    total_uploaded += 1
                    log_success(f"✅ Cardápio enviado com sucesso!")
                else:
                    log_error(f"❌ Falha ao enviar para Firebase")
            else:
                log_error(f"❌ Falha ao processar PDF")
                
        except Exception as e:
            log_error(f"Erro ao processar {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Resumo final
    log_info(f"\n{'=' * 60}")
    log_info("RESUMO DO PROCESSAMENTO")
    log_info(f"{'=' * 60}")
    log_info(f"PDFs baixados: {len(pdf_files)}")
    log_info(f"PDFs processados com sucesso: {total_processed}")
    log_info(f"Cardápios enviados ao Firebase: {total_uploaded}")
    log_info(f"{'=' * 60}")
    
    # Limpar diretório temporário se foi criado
    if not test_pdf.exists() and 'temp_dir' in locals():
        import shutil
        try:
            shutil.rmtree(temp_dir)
            log_info("Diretório temporário removido")
        except Exception as e:
            log_warning(f"Erro ao remover diretório temporário: {e}")
    
    return 0 if total_uploaded > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
