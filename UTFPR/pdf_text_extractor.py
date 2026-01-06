#!/usr/bin/env python3
"""
PDF Text Extractor - Extracts text from PDFs locally before API call.
Uses pdfplumber for superior table/text extraction.
"""

import os
from typing import Optional

try:
    import pdfplumber
    HAVE_PDFPLUMBER = True
except ImportError:
    HAVE_PDFPLUMBER = False
    print("[AVISO] pdfplumber não instalado. Instale com: pip install pdfplumber")


def extract_text_from_pdf(pdf_path: str, min_chars: int = 100) -> Optional[str]:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        min_chars: Minimum characters required for valid extraction
        
    Returns:
        Extracted text or None if extraction fails/insufficient
    """
    if not HAVE_PDFPLUMBER:
        print("[AVISO] pdfplumber não disponível, pulando extração de texto")
        return None
    
    if not os.path.exists(pdf_path):
        print(f"[ERRO] Arquivo não encontrado: {pdf_path}")
        return None
    
    try:
        print(f"[INFO] Extraindo texto do PDF: {os.path.basename(pdf_path)}")
        
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Try to extract tables first (better for menu structure)
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                # Filter out None values and join
                                row_text = " | ".join(str(cell) for cell in row if cell)
                                if row_text.strip():
                                    all_text.append(row_text)
                else:
                    # Fall back to regular text extraction
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
        
        combined_text = "\n".join(all_text)
        
        # Check if we got enough content
        if len(combined_text) < min_chars:
            print(f"[AVISO] Texto extraído muito curto ({len(combined_text)} chars). PDF pode ser baseado em imagem.")
            return None
        
        print(f"[OK] Extraídos {len(combined_text)} caracteres do PDF")
        return combined_text
        
    except Exception as e:
        print(f"[ERRO] Falha ao extrair texto do PDF: {e}")
        return None


def is_text_based_pdf(pdf_path: str) -> bool:
    """
    Check if a PDF contains extractable text.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        True if the PDF has extractable text, False otherwise
    """
    text = extract_text_from_pdf(pdf_path, min_chars=50)
    return text is not None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python pdf_text_extractor.py <caminho_do_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)
    
    if text:
        print("\n" + "=" * 60)
        print("TEXTO EXTRAÍDO:")
        print("=" * 60)
        print(text[:2000])  # Print first 2000 chars
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} caracteres adicionais)")
    else:
        print("Falha na extração de texto")
        sys.exit(1)
