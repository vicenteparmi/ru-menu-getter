#!/usr/bin/env python3
"""
Módulo para upload de cardápios dos RUs para o Firebase.
Compatível com o formato usado pelos scripts em Ruby (UFPR.rb).
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def upload_menu_to_firebase(menu_data: Dict[str, Any], ru_name: str, city: str = "ufsc") -> bool:
    """
    Faz upload de cardápio para o Firebase seguindo o padrão do UFPR.rb
    
    Args:
        menu_data: Dados do cardápio no formato JSON
        ru_name: Nome do RU (ex: "blumenau", "joinville")
        city: Cidade/Universidade (default: "ufsc")
    
    Returns:
        True se o upload foi bem-sucedido, False caso contrário
    """
    # Verificar variáveis de ambiente
    base_url = os.environ.get('BASE_URL')
    firebase_key = os.environ.get('FIREBASE_KEY')
    
    if not base_url or not firebase_key:
        print("⚠️ Variáveis de ambiente BASE_URL e FIREBASE_KEY não configuradas")
        return False
    
    if not requests:
        print("⚠️ Biblioteca requests não instalada. Execute: pip install requests")
        return False
    
    success_count = 0
    total_count = 0
    
    try:
        for date_str, day_data in menu_data.items():
            total_count += 1
            
            # Validar formato da data
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                print(f"❌ Data inválida: {date_str}")
                continue
            
            # Preparar dados no formato do Firebase
            firebase_data = {
                'weekday': day_data.get('weekday', 'Dia não especificado'),
                'menu': day_data.get('menu', []),
                'timestamp': day_data.get('timestamp', int(time.time()))
            }
            
            # URL para o Firebase
            firebase_url = f"{base_url}/menus/{city}/rus/{ru_name}/menus/{date_str}.json?auth={firebase_key}"
            
            # Fazer upload
            response = requests.put(firebase_url, json=firebase_data, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Upload bem-sucedido: {ru_name} - {date_str}")
                success_count += 1
            else:
                print(f"❌ Falha no upload: {ru_name} - {date_str} (HTTP {response.status_code})")
                print(f"   Resposta: {response.text[:200]}...")
            
            # Pequena pausa para evitar rate limiting
            time.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Erro durante upload: {e}")
        return False
    
    print(f"\n📊 Resumo do upload:")
    print(f"   Total de dias: {total_count}")
    print(f"   Uploads bem-sucedidos: {success_count}")
    print(f"   Falhas: {total_count - success_count}")
    
    return success_count > 0

def upload_approved_menus(jsons_dir: str = None, city: str = "ufsc") -> Dict[str, bool]:
    """
    Faz upload de todos os cardápios aprovados para o Firebase
    
    Args:
        jsons_dir: Diretório com arquivos JSON (default: jsons/)
        city: Cidade/Universidade (default: "ufsc")
    
    Returns:
        Dicionário com resultados do upload {arquivo: sucesso}
    """
    if jsons_dir is None:
        jsons_dir = os.path.join(os.path.dirname(__file__), "..", "jsons")
    
    results = {}
    
    # Buscar arquivos JSON
    import glob
    json_files = glob.glob(os.path.join(jsons_dir, "*.json"))
    
    if not json_files:
        print("⚠️ Nenhum arquivo JSON encontrado")
        return results
    
    print(f"🔍 Encontrados {len(json_files)} arquivos JSON")
    
    for json_file in json_files:
        file_name = os.path.basename(json_file)
        ru_name = file_name.replace('.json', '')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            
            # Verificar se há dados aprovados
            approved_data = {}
            for date_str, day_data in menu_data.items():
                if day_data.get('approved', False):
                    approved_data[date_str] = day_data
            
            if not approved_data:
                print(f"⏭️ Pulando {file_name}: nenhum cardápio aprovado")
                results[file_name] = False
                continue
            
            print(f"\n📤 Fazendo upload de {file_name} ({len(approved_data)} dias aprovados)...")
            success = upload_menu_to_firebase(approved_data, ru_name, city)
            results[file_name] = success
            
        except Exception as e:
            print(f"❌ Erro ao processar {file_name}: {e}")
            results[file_name] = False
    
    return results

def test_firebase_connection() -> bool:
    """
    Testa a conexão com o Firebase
    
    Returns:
        True se a conexão foi bem-sucedida
    """
    base_url = os.environ.get('BASE_URL')
    firebase_key = os.environ.get('FIREBASE_KEY')
    
    if not base_url or not firebase_key:
        print("⚠️ Variáveis de ambiente não configuradas")
        return False
    
    if not requests:
        print("⚠️ Biblioteca requests não instalada")
        return False
    
    try:
        # Fazer uma requisição de teste
        test_url = f"{base_url}/test.json?auth={firebase_key}"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Conexão com Firebase bem-sucedida")
            return True
        else:
            print(f"❌ Falha na conexão: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

if __name__ == "__main__":
    # Teste básico
    print("🧪 Testando conexão com Firebase...")
    if test_firebase_connection():
        print("\n📤 Fazendo upload de cardápios aprovados...")
        results = upload_approved_menus()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"\n🎯 Resultado final: {success_count}/{total_count} uploads bem-sucedidos")
    else:
        print("❌ Não foi possível conectar ao Firebase")
