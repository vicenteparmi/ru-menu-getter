#!/usr/bin/env python3
"""
Gemini PDF Processor - Processa PDFs usando a API do Gemini
Otimizado com extração de texto local e structured outputs.
"""

import os
import base64
import time
from datetime import datetime
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from models import get_menu_json_schema, validate_menu_data
from pdf_text_extractor import extract_text_from_pdf


def get_current_year() -> int:
    """Returns the current year for dynamic date handling."""
    return datetime.now().year


def configure_gemini():
    """Configura a API do Gemini com a chave de API."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY ou GOOGLE_API_KEY não definida nas variáveis de ambiente")
    
    return genai.Client(api_key=api_key)


def get_system_instruction() -> str:
    """Returns the system instruction with dynamic year."""
    current_year = get_current_year()
    
    return f"""
Você deve extrair e estruturar as informações de cardápio do restaurante universitário em formato JSON.
Siga EXATAMENTE o formato especificado abaixo.

REGRAS IMPORTANTES:
1. Use APENAS o formato YYYY-MM-DD para datas
2. Use {current_year} como o ano para todas as datas (ano atual)
3. Cada dia deve ter: menu (array de arrays), timestamp (sempre 0), weekday (dia da semana em português)
4. O array 'menu' representa 3 refeições: [café da manhã/lanche, almoço, jantar]
5. Se não houver informação para uma refeição, use EXATAMENTE ["Sem refeições disponíveis"]
6. Capitalize adequadamente os nomes dos pratos
7. Mantenha opções vegetarianas/veganas quando presentes
8. Inclua acompanhamentos e saladas quando mencionados

FORMATO DE SAÍDA (JSON válido, sem comentários):
{{
  "{current_year}-01-06": {{
    "menu": [
      ["Sem refeições disponíveis"],
      ["Bife acebolado", "Opção vegana: hambúrguer de feijão", "Arroz", "Feijão", "Salada verde"],
      ["Frango grelhado", "Opção vegetariana: lasanha de berinjela", "Purê de batata", "Salada mista"]
    ],
    "timestamp": 0,
    "weekday": "Segunda-Feira"
  }}
}}

Retorne APENAS o JSON válido do cardápio, sem texto adicional.
"""


def clean_response_text(text: str) -> str:
    """Remove markdown code blocks from response."""
    text = text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()


def process_text_with_gemini(text_content: str, model_name: str = "gemini-flash-latest") -> str:
    """
    Process extracted text with Gemini (cheaper than sending full PDF).
    
    Args:
        text_content: Extracted text from PDF
        model_name: Gemini model to use
        
    Returns:
        JSON string of menu data
    """
    client = configure_gemini()
    
    print(f"[INFO] Processando texto extraído com {model_name}...")
    print(f"[INFO] Tamanho do texto: {len(text_content)} caracteres")
    
    # Create content with text
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"Extraia o cardápio do seguinte conteúdo:\n\n{text_content}")
            ],
        ),
    ]
    
    # Configure with structured output
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2100,
        ),
        system_instruction=[
            types.Part.from_text(text=get_system_instruction()),
        ],
        response_mime_type="application/json",
    )
    
    # Generate content
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )
    
    text = clean_response_text(response.text)
    print(f"[OK] Resposta recebida: {len(text)} caracteres")
    
    return text


def upload_pdf_to_gemini(client: genai.Client, pdf_path: str, display_name: str = None) -> Any:
    """
    Faz upload de um PDF para a API File do Gemini.
    
    Args:
        client: Cliente do Gemini
        pdf_path: Caminho para o arquivo PDF
        display_name: Nome para exibição (opcional)
    
    Returns:
        Objeto do arquivo enviado
    """
    if display_name is None:
        display_name = os.path.basename(pdf_path)
    
    print(f"[INFO] Fazendo upload de {display_name} para Gemini...")
    
    # Upload do arquivo
    file = client.files.upload(path=pdf_path)
    print(f"[OK] Upload concluído: {file.uri}")
    
    # Aguardar processamento
    print("[INFO] Aguardando processamento do arquivo...")
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = client.files.get(name=file.name)
    
    if file.state.name == "FAILED":
        raise ValueError(f"Falha no processamento do PDF: {file.state.name}")
    
    print(f"[OK] Arquivo processado e pronto para uso")
    return file


def process_pdf_with_gemini(pdf_path: str, model_name: str = "gemini-flash-latest") -> str:
    """
    Processa um PDF usando a API do Gemini (File API para arquivos grandes).
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        model_name: Nome do modelo Gemini a usar
    
    Returns:
        JSON estruturado do cardápio
    """
    client = configure_gemini()
    
    # Upload do PDF
    file = upload_pdf_to_gemini(client, pdf_path)
    
    print(f"[INFO] Processando PDF com {model_name}...")
    
    # Configurar conteúdo e configuração
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=file.uri,
                    mime_type=file.mime_type
                )
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2100,
        ),
        system_instruction=[
            types.Part.from_text(text=get_system_instruction()),
        ],
        response_mime_type="application/json",
    )
    
    # Gerar conteúdo
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )
    
    text = clean_response_text(response.text)
    print(f"[OK] Resposta recebida: {len(text)} caracteres")
    
    # Deletar arquivo após uso
    try:
        client.files.delete(name=file.name)
        print(f"[INFO] Arquivo temporário removido")
    except Exception as e:
        print(f"[AVISO] Não foi possível remover arquivo: {e}")
    
    return text


def process_pdf_inline(pdf_path: str, model_name: str = "gemini-flash-latest") -> str:
    """
    Processa um PDF com estratégia otimizada:
    1. Tenta extrair texto localmente primeiro (mais barato)
    2. Se falhar, envia PDF inline para arquivos <20MB
    3. Usa File API para arquivos maiores
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        model_name: Nome do modelo Gemini a usar
    
    Returns:
        JSON estruturado do cardápio
    """
    # ESTRATÉGIA 1: Tentar extrair texto localmente (mais barato)
    extracted_text = extract_text_from_pdf(pdf_path)
    
    if extracted_text:
        print("[INFO] Usando texto extraído localmente (modo econômico)")
        return process_text_with_gemini(extracted_text, model_name)
    
    # ESTRATÉGIA 2: Verificar tamanho do arquivo
    file_size = os.path.getsize(pdf_path)
    
    if file_size > 20 * 1024 * 1024:  # 20 MB
        print("[AVISO] Arquivo maior que 20MB, usando File API")
        return process_pdf_with_gemini(pdf_path, model_name)
    
    # ESTRATÉGIA 3: Enviar PDF inline
    print(f"[INFO] Processando PDF inline ({file_size / 1024:.1f} KB)...")
    
    client = configure_gemini()
    
    # Ler PDF como bytes (não precisa de base64 com from_bytes)
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Criar conteúdo usando from_bytes (API correta para google-genai)
    contents = [
        types.Part.from_bytes(
            data=pdf_data,
            mime_type="application/pdf"
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2100,
        ),
        system_instruction=[
            types.Part.from_text(text=get_system_instruction()),
        ],
        response_mime_type="application/json",
    )
    
    # Gerar conteúdo
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )
    
    text = clean_response_text(response.text)
    print(f"[OK] Resposta recebida: {len(text)} caracteres")
    
    return text


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python gemini_pdf_processor.py <caminho_do_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Erro: Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    print(f"Processando: {pdf_path}")
    print(f"Ano atual: {get_current_year()}")
    
    try:
        result = process_pdf_inline(pdf_path)
        print("\n" + "=" * 60)
        print("RESULTADO:")
        print("=" * 60)
        print(result)
        
        # Validate result
        import json
        data = json.loads(result)
        is_valid, processed, errors = validate_menu_data(data)
        
        if is_valid:
            print("\n[OK] JSON validado com sucesso!")
        else:
            print(f"\n[AVISO] Erros de validação: {errors}")
            
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
