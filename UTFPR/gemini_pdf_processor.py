#!/usr/bin/env python3
"""
Gemini PDF Processor - Processa PDFs usando a API do Gemini
"""

import os
import base64
import time
from typing import Optional, Dict, Any
import google.generativeai as genai


def configure_gemini():
    """Configura a API do Gemini com a chave de API."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY ou GOOGLE_API_KEY não definida nas variáveis de ambiente")
    
    genai.configure(api_key=api_key)


def upload_pdf_to_gemini(pdf_path: str, display_name: str = None) -> Any:
    """
    Faz upload de um PDF para a API File do Gemini.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        display_name: Nome para exibição (opcional)
    
    Returns:
        Objeto do arquivo enviado
    """
    if display_name is None:
        display_name = os.path.basename(pdf_path)
    
    print(f"[INFO] Fazendo upload de {display_name} para Gemini...")
    
    # Upload do arquivo
    file = genai.upload_file(pdf_path, mime_type="application/pdf")
    print(f"[OK] Upload concluído: {file.uri}")
    
    # Aguardar processamento
    print("[INFO] Aguardando processamento do arquivo...")
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    
    if file.state.name == "FAILED":
        raise ValueError(f"Falha no processamento do PDF: {file.state.name}")
    
    print(f"[OK] Arquivo processado e pronto para uso")
    return file


def process_pdf_with_gemini(pdf_path: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Processa um PDF usando a API do Gemini e extrai informações de cardápio.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        model_name: Nome do modelo Gemini a usar
    
    Returns:
        JSON estruturado do cardápio
    """
    configure_gemini()
    
    # Upload do PDF
    file = upload_pdf_to_gemini(pdf_path)
    
    # Criar prompt para extração de cardápio
    prompt = """
Extract the content from the PDF by meal. Give only the content.

Given a text with the menu meals content, return the JSON for the menu using the specified format. Capitalize words on the menu content. We are in 2025.

IMPORTANT: Always use 2025 as the year, regardless of what appears in the PDF. Convert all dates to 2025.

Here is a example of output (using comments only as a reference for the output)

{
  "2025-04-14": { // The date is variable and must be in this format: YYYY-MM-DD. One of this objects for each date.
    "menu": [
      [
"Sem refeições disponíveis" // Displayed if not informed, exactaly like that
      ],
      [ // This is the space for almoço, each item in one line. Set category if present in parentesis
        "Bife acebolado",
        "Opção vegana: hambúrguer de feijão cavalo",
        "Opção: ovo frito",
        "Berinjela à portuguesa",
        "Saladas: folhosa e beterraba ralada",
        "Mamão"
      ],
      [ // This is jantar
        "Cubos de frango acebolado",
        "Opção vegana: bolinho de lentilha",
        "Opção: cozido",
        "Batata doce doré",
        "Saladas: folhosa e tabule"
      ]
    ],
    "timestamp": 0, // Always zero. It will be replaced later
    "weekday": "Segunda-Feira" // The week day
  }
}
"""
    
    # Configurar modelo
    model = genai.GenerativeModel(model_name)
    
    print(f"[INFO] Processando PDF com {model_name}...")
    
    # Enviar prompt com o arquivo
    response = model.generate_content([file, prompt])
    
    # Limpar resposta
    text = response.text.strip()
    
    # Remover marcadores de código markdown se presentes
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    print(f"[OK] Resposta recebida: {len(text)} caracteres")
    
    # Deletar arquivo após uso (opcional, arquivos expiram em 48h)
    try:
        genai.delete_file(file.name)
        print(f"[INFO] Arquivo temporário removido")
    except Exception as e:
        print(f"[AVISO] Não foi possível remover arquivo: {e}")
    
    return text


def process_pdf_inline(pdf_path: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Processa um PDF pequeno (<20MB) enviando dados inline (base64).
    Mais rápido para arquivos pequenos, sem necessidade de File API.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        model_name: Nome do modelo Gemini a usar
    
    Returns:
        JSON estruturado do cardápio
    """
    configure_gemini()
    
    # Verificar tamanho do arquivo
    file_size = os.path.getsize(pdf_path)
    if file_size > 20 * 1024 * 1024:  # 20 MB
        print("[AVISO] Arquivo maior que 20MB, use process_pdf_with_gemini()")
        return process_pdf_with_gemini(pdf_path, model_name)
    
    print(f"[INFO] Processando PDF inline ({file_size / 1024:.1f} KB)...")
    
    # Ler e codificar PDF em base64
    with open(pdf_path, 'rb') as f:
        pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')
    
    # Criar prompt
    prompt = """
Você deve extrair e estruturar as informações de cardápio do restaurante universitário em formato JSON.
Siga EXATAMENTE o formato especificado abaixo.

REGRAS IMPORTANTES:
1. Use APENAS o formato YYYY-MM-DD para datas
2. Cada dia deve ter: menu (array de arrays), timestamp (sempre 0), weekday (dia da semana em português)
3. O array 'menu' representa as refeições: [café da manhã/lanche, almoço, jantar]
4. Se não houver informação para uma refeição, use EXATAMENTE ['Sem refeições disponíveis']
5. Capitalize adequadamente os nomes dos pratos
6. Mantenha opções vegetarianas/veganas quando presentes
7. Inclua acompanhamentos e saladas quando mencionados

FORMATO DE SAÍDA (JSON válido, sem comentários):
{
  "2025-06-05": {
    "menu": [
      ["Sem refeições disponíveis"],
      ["Bife acebolado", "Opção vegana: hambúrguer de feijão", "Arroz", "Feijão", "Salada verde"],
      ["Frango grelhado", "Opção vegetariana: lasanha de berinjela", "Purê de batata", "Salada mista"]
    ],
    "timestamp": 0,
    "weekday": "Quinta-Feira"
  }
}

Analise o PDF e retorne APENAS o JSON válido do cardápio, sem texto adicional.
"""
    
    # Configurar modelo
    model = genai.GenerativeModel(model_name)
    
    # Criar parte do documento
    document_part = {
        "inline_data": {
            "mime_type": "application/pdf",
            "data": pdf_data
        }
    }
    
    # Enviar prompt com o documento
    response = model.generate_content([document_part, prompt])
    
    # Limpar resposta
    text = response.text.strip()
    
    # Remover marcadores de código markdown se presentes
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
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
    
    try:
        # Tentar método inline primeiro (mais rápido)
        result = process_pdf_inline(pdf_path)
        print("\n" + "=" * 60)
        print("RESULTADO:")
        print("=" * 60)
        print(result)
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
