#!/usr/bin/env python3
"""
Utilitário para validar e normalizar JSONs de cardápios.
Este script pode ser usado para processar arquivos JSON individuais ou em lote.
"""

import json
import sys
import os
import argparse
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.json_validator import (
    comprehensive_json_validator,
    extract_and_validate_json,
    validate_json_format,
    NO_MEALS_TEXT
)


def validate_and_fix_json_file(file_path: str, output_path: str = None, verbose: bool = True) -> bool:
    """
    Valida e corrige um arquivo JSON, salvando o resultado.
    
    Args:
        file_path: Caminho para o arquivo JSON de entrada
        output_path: Caminho para salvar o JSON corrigido (opcional)
        verbose: Se True, mostra informações detalhadas
    
    Returns:
        bool: True se a validação foi bem-sucedida
    """
    if not os.path.exists(file_path):
        if verbose:
            print(f"❌ Arquivo não encontrado: {file_path}")
        return False
    
    try:
        # Carregar JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print(f"📁 Processando: {os.path.basename(file_path)}")
            print(f"📊 Dados originais: {len(data)} datas")
        
        # Validar e processar
        is_valid, processed_data, errors = comprehensive_json_validator(data)
        
        if verbose:
            status = "✅ VÁLIDO" if is_valid else "⚠️  COM PROBLEMAS"
            print(f"🔍 Status: {status}")
            print(f"📝 Erros encontrados: {len(errors)}")
            
            if errors and len(errors) <= 5:
                for error in errors:
                    print(f"   • {error}")
            elif errors:
                print(f"   • {errors[0]}")
                print(f"   • ... e mais {len(errors)-1} erros")
        
        # Determinar caminho de saída
        if output_path is None:
            output_path = file_path  # Sobrescrever arquivo original
        
        # Salvar JSON processado
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        if verbose:
            if output_path == file_path:
                print(f"💾 Arquivo atualizado: {os.path.basename(file_path)}")
            else:
                print(f"💾 Arquivo salvo: {os.path.basename(output_path)}")
        
        return is_valid
        
    except Exception as e:
        if verbose:
            print(f"❌ Erro ao processar arquivo: {e}")
        return False


def process_directory(directory: str, pattern: str = "*.json", verbose: bool = True) -> dict:
    """
    Processa todos os arquivos JSON em um diretório.
    
    Args:
        directory: Diretório para processar
        pattern: Padrão de arquivos a processar
        verbose: Se True, mostra informações detalhadas
    
    Returns:
        dict: Relatório com resultados {arquivo: sucesso}
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        if verbose:
            print(f"❌ Diretório não encontrado: {directory}")
        return {}
    
    json_files = list(directory_path.glob(pattern))
    
    if not json_files:
        if verbose:
            print(f"❌ Nenhum arquivo JSON encontrado em: {directory}")
        return {}
    
    if verbose:
        print(f"📂 Processando {len(json_files)} arquivos em: {directory}")
        print("=" * 60)
    
    results = {}
    for file_path in json_files:
        if verbose:
            print(f"\n📄 {file_path.name}")
            print("-" * 40)
        
        success = validate_and_fix_json_file(str(file_path), verbose=verbose)
        results[file_path.name] = success
    
    if verbose:
        print("\n" + "=" * 60)
        print("📊 RESUMO FINAL")
        print("=" * 60)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        for filename, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {filename}")
        
        print(f"\n🎯 Resultado: {successful}/{total} arquivos processados com sucesso")
        
        if successful == total:
            print("🎉 Todos os arquivos foram processados com sucesso!")
        elif successful > 0:
            print(f"⚠️  {total - successful} arquivo(s) tiveram problemas")
        else:
            print("❌ Nenhum arquivo foi processado com sucesso")
    
    return results


def validate_ai_response(response_text: str, verbose: bool = True) -> dict:
    """
    Valida uma resposta de IA e extrai JSON estruturado.
    
    Args:
        response_text: Texto da resposta da IA
        verbose: Se True, mostra informações detalhadas
    
    Returns:
        dict: JSON extraído e validado
    """
    if verbose:
        print("🤖 Validando resposta da IA...")
        print("-" * 40)
    
    # Extrair JSON
    extracted_json = extract_and_validate_json(response_text)
    
    if not extracted_json:
        if verbose:
            print("❌ Não foi possível extrair JSON válido da resposta")
        return {}
    
    # Validar e processar
    is_valid, processed_data, errors = comprehensive_json_validator(extracted_json)
    
    if verbose:
        print(f"📥 JSON extraído: {len(extracted_json)} datas")
        print(f"🔍 Validação: {'✅ VÁLIDA' if is_valid else '⚠️  COM PROBLEMAS'}")
        print(f"📝 Erros: {len(errors)}")
        
        if errors:
            for error in errors[:3]:
                print(f"   • {error}")
            if len(errors) > 3:
                print(f"   • ... e mais {len(errors)-3} erros")
        
        # Verificar se contém o texto padronizado
        has_standard_text = False
        for date, day_data in processed_data.items():
            for meal in day_data.get('menu', []):
                if NO_MEALS_TEXT in meal:
                    has_standard_text = True
                    break
            if has_standard_text:
                break
        
        if has_standard_text:
            print(f"✨ Contém texto padronizado: '{NO_MEALS_TEXT}'")
    
    return processed_data


def main():
    """Função principal do utilitário."""
    parser = argparse.ArgumentParser(
        description="Validador e normalizador de JSONs de cardápios dos RUs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Validar um arquivo específico
  python3 json_util.py arquivo.json

  # Validar todos os JSONs em um diretório
  python3 json_util.py --dir jsons/

  # Validar arquivo e salvar cópia corrigida
  python3 json_util.py arquivo.json --output arquivo_corrigido.json

  # Processar diretório silenciosamente
  python3 json_util.py --dir jsons/ --quiet

  # Testar resposta de IA (modo interativo)
  python3 json_util.py --ai-response
        """
    )
    
    parser.add_argument(
        'file', 
        nargs='?', 
        help='Arquivo JSON para validar'
    )
    
    parser.add_argument(
        '--dir', 
        help='Diretório contendo arquivos JSON para processar'
    )
    
    parser.add_argument(
        '--output', 
        help='Arquivo de saída (opcional)'
    )
    
    parser.add_argument(
        '--quiet', 
        action='store_true', 
        help='Modo silencioso (menos output)'
    )
    
    parser.add_argument(
        '--ai-response',
        action='store_true',
        help='Modo interativo para testar resposta de IA'
    )
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    if args.ai_response:
        # Modo interativo para testar resposta de IA
        print("🤖 MODO TESTE DE RESPOSTA IA")
        print("=" * 50)
        print("Cole a resposta da IA abaixo (terminar com linha vazia):")
        
        lines = []
        while True:
            try:
                line = input()
                if not line.strip():
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        
        if lines:
            response_text = '\n'.join(lines)
            result = validate_ai_response(response_text, verbose=True)
            
            if result:
                print("\n📄 JSON processado:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("\n❌ Não foi possível processar a resposta")
        else:
            print("❌ Nenhuma resposta fornecida")
    
    elif args.dir:
        # Processar diretório
        process_directory(args.dir, verbose=verbose)
    
    elif args.file:
        # Processar arquivo único
        success = validate_and_fix_json_file(args.file, args.output, verbose=verbose)
        if not success:
            sys.exit(1)
    
    else:
        # Se nenhum argumento for fornecido, tentar processar diretório jsons/
        jsons_dir = os.path.join(os.path.dirname(__file__), "jsons")
        if os.path.exists(jsons_dir):
            if verbose:
                print("📂 Nenhum arquivo especificado, processando diretório jsons/")
            process_directory(jsons_dir, verbose=verbose)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
