#!/usr/bin/env python3
"""
Módulo para upload de cardápios dos RUs para o Firebase.
Segue exatamente a mesma lógica dos scripts Ruby (UFPR.rb e UFRGS.rb).

PADRÃO PARA UFSC: Usa sempre archive/menus/ (use_archive=True)
Este é o caminho padrão seguindo o modelo UFRGS.rb para dados arquivados.

Estrutura UFSC no Firebase (seguindo modelo UFPR.rb):
data = {
  "ufsc-blu" => { "rus" => { "blumenau" => {} } },
  "ufsc-cur" => { "rus" => { "curitibanos" => {} } },
  "ufsc-flo" => { "rus" => { "ccal" => {}, "trindade" => {} } },
  "ufsc-joi" => { "rus" => { "joinville" => {} } }
}

Exemplo de path: archive/menus/ufsc-blu/rus/blumenau/menus/2024-01-15
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

# Carrega variáveis do .env se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def is_menu_fully_unavailable(menu):
    """Retorna True se todas as refeições do dia forem ['Sem refeições disponíveis']."""
    if not isinstance(menu, list) or len(menu) != 3:
        return False
    return all(
        isinstance(period, list) and len(period) == 1 and period[0] == "Sem refeições disponíveis"
        for period in menu
    )

def upload_menu_to_firebase(menu_data: Dict[str, Any], ru_name: str, use_archive: bool = True) -> bool:
    """
    Faz upload de cardápio para o Firebase seguindo exatamente o padrão do UFPR.rb
    
    Estrutura UFSC no Firebase (seguindo modelo UFPR.rb):
    data = {
      "ufsc-blu" => { "rus" => { "blumenau" => {} } },
      "ufsc-cur" => { "rus" => { "curitibanos" => {} } },
      "ufsc-flo" => { "rus" => { "ccal" => {}, "trindade" => {} } },
      "ufsc-joi" => { "rus" => { "joinville" => {} } }
    }
    
    Exemplo de path: menus/ufsc-blu/rus/blumenau/menus/2024-01-15
    
    UFPR.rb equivalente:
    response = firebase.set("menus/#{city}/rus/#{name}/menus/#{element[0]}", 
                           { :weekday => element[1], :menu => element[2], :timestamp => element[3] })
    
    Timestamp: Se for 0 ou inexistente no JSON, usa Time.now.to_i (timestamp Unix atual)
    exatamente como o UFPR.rb faz na linha 175: Time.now.to_i
    
    Args:
        menu_data: Dados do cardápio no formato JSON
        ru_name: Nome do RU (ex: "blumenau", "joinville") 
        use_archive: Se True, usa "archive/menus" como no UFRGS.rb (PADRÃO), senão "menus" como no UFPR.rb
    
    Returns:
        True se o upload foi bem-sucedido, False caso contrário
    """
    # Estrutura UFSC seguindo o modelo UFPR.rb:
    # data = {
    #   "ufsc-blu" => { "rus" => { "blumenau" => {} } },
    #   "ufsc-cur" => { "rus" => { "curitibanos" => {} } },
    #   "ufsc-flo" => { "rus" => { "ccal" => {}, "trindade" => {} } },
    #   "ufsc-joi" => { "rus" => { "joinville" => {} } }
    # }
    
    # Mapeamento UFSC: RU -> código da cidade
    UFSC_MAPPING = {
        'blumenau': 'ufsc-blu',
        'curitibanos': 'ufsc-cur', 
        'cca': 'ufsc-flo',
        'trindade': 'ufsc-flo',
        'joinville': 'ufsc-joi'
    }
    
    # Mapear o RU para o código correto da cidade
    city_code = UFSC_MAPPING.get(ru_name)
    if not city_code:
        print(f"[UPLOAD ERROR] RU '{ru_name}' não encontrado no mapeamento UFSC")
        print(f"[UPLOAD ERROR] RUs válidos: {list(UFSC_MAPPING.keys())}")
        return False
    
    # Verificar variáveis de ambiente (mesmo padrão do Ruby)
    base_url = os.environ.get('BASE_URL')
    firebase_key = os.environ.get('FIREBASE_KEY')
    
    if not base_url or not firebase_key:
        print("[UPLOAD ERROR] Variáveis de ambiente BASE_URL e FIREBASE_KEY não configuradas")
        print("[UPLOAD ERROR] Configure as variáveis no arquivo .env ou variáveis de ambiente do sistema")
        return False
    
    if not requests:
        print("[UPLOAD ERROR] Biblioteca requests não instalada. Execute: pip install requests")
        return False
    
    success_count = 0
    total_count = 0
    
    print(f"[GETTING DATA > {city_code} > {ru_name}] Starting upload...")
    
    try:
        for date_str, day_data in menu_data.items():
            # Novo filtro: pular datas com todas as refeições indisponíveis
            menu = day_data.get('menu', [])
            if is_menu_fully_unavailable(menu):
                print(f"[GETTING DATA > {city_code} > {ru_name}] Dia {date_str} ignorado: todas as refeições indisponíveis.")
                continue
            total_count += 1
            
            # Validar formato da data (YYYY-MM-DD)
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                print(f"[GETTING DATA > {city_code} > {ru_name}] Error parsing date: invalid format ({date_str}). Skipping...")
                continue
            
            # Preparar dados exatamente como no Ruby
            # UFPR.rb: { :weekday => element[1], :menu => element[2], :timestamp => element[3] }
            # UFRGS.rb: { menu: menus_array, weekday: weekday, timestamp: Time.now.to_i }
            
            # Obter timestamp - se for 0 ou não existir, usar timestamp atual (mesmo padrão do UFPR.rb)
            timestamp = day_data.get('timestamp', 0)
            if timestamp == 0:
                timestamp = int(time.time())  # Time.now.to_i equivalente em Python
            
            firebase_data = {
                'weekday': day_data.get('weekday', 'Dia não especificado'),
                'menu': day_data.get('menu', []),
                'timestamp': timestamp
            }
            
            # URL exata do Firebase seguindo padrão Ruby
            # Para UFSC usamos sempre o padrão UFPR.rb com o código da cidade correto
            if use_archive:
                # Padrão UFRGS.rb: "archive/menus/#{city}/rus/#{ru_key}/menus/#{date_str}"
                firebase_path = f"archive/menus/{city_code}/rus/{ru_name}/menus/{date_str}"
            else:
                # Padrão UFPR.rb: "menus/#{city}/rus/#{name}/menus/#{element[0]}"
                firebase_path = f"menus/{city_code}/rus/{ru_name}/menus/{date_str}"
            
            firebase_url = f"{base_url}/{firebase_path}.json?auth={firebase_key}"
            
            # Fazer upload
            # UFPR.rb usa firebase.set() = PUT request
            # UFRGS.rb usa firebase.update() = PATCH request, mas para compatibilidade usaremos PUT
            response = requests.put(firebase_url, json=firebase_data, timeout=30)
            
            if response.status_code == 200:
                print(f"[GETTING DATA > {city_code} > {ru_name}] Response: {response.status_code}. Finished for {date_str}.")
                success_count += 1
            else:
                print(f"[GETTING DATA > {city_code} > {ru_name}] Response: {response.status_code}. Error for {date_str}.")
                print(f"[GETTING DATA > {city_code} > {ru_name}] Error details: {response.text[:200]}...")
            
            # Pequena pausa para evitar bloqueio (mesmo conceito do Ruby)
            # UFPR.rb usa sleep(10), UFRGS.rb usa sleep(2)
            # Usaremos 1 segundo para ser mais rápido
            time.sleep(1)
            
    except Exception as e:
        print(f"[GETTING DATA > {city_code} > {ru_name}] Error during upload: {e}")
        return False
    
    print(f"[GETTING DATA > {city_code} > {ru_name}] Upload summary:")
    print(f"[GETTING DATA > {city_code} > {ru_name}] Total days: {total_count}")
    print(f"[GETTING DATA > {city_code} > {ru_name}] Successful uploads: {success_count}")
    print(f"[GETTING DATA > {city_code} > {ru_name}] Failures: {total_count - success_count}")
    
    return success_count > 0

def upload_approved_menus(jsons_dir: Optional[str] = None, use_archive: bool = True) -> Dict[str, bool]:
    """
    Faz upload de todos os cardápios aprovados para o Firebase
    Segue a lógica dos scripts Ruby de processar múltiplos RUs
    
    Estrutura UFSC (seguindo modelo UFPR.rb):
    - ufsc-blu -> rus -> blumenau
    - ufsc-cur -> rus -> curitibanos  
    - ufsc-flo -> rus -> ccal, trindade
    - ufsc-joi -> rus -> joinville
    
    Args:
        jsons_dir: Diretório com arquivos JSON (default: jsons/)
        use_archive: Se True, usa "archive/menus" como no UFRGS.rb (padrão = True)
    
    Returns:
        Dicionário com resultados do upload {arquivo: sucesso}
    """
    if jsons_dir is None:
        jsons_dir = os.path.join(os.path.dirname(__file__), "..", "jsons")
    
    results = {}
    
    # Buscar arquivos JSON (equivalente ao loop pelos RUs no Ruby)
    import glob
    json_files = glob.glob(os.path.join(jsons_dir, "*.json"))
    
    if not json_files:
        print("[UPLOAD ERROR] Nenhum arquivo JSON encontrado")
        return results
    
    print(f"[UPLOAD INFO] Encontrados {len(json_files)} arquivos JSON")
    
    for json_file in json_files:
        file_name = os.path.basename(json_file)
        ru_name = file_name.replace('.json', '')
        
        print(f"[GETTING DATA > UFSC] Starting {ru_name}...")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            
            # Verificar se há dados aprovados
            approved_data = {}
            for date_str, day_data in menu_data.items():
                if day_data.get('approved', False):
                    approved_data[date_str] = day_data
            
            if not approved_data:
                print(f"[GETTING DATA > UFSC] No approved menus found for {ru_name}. Skipping...")
                results[file_name] = False
                continue
            
            print(f"[GETTING DATA > UFSC] Processing {ru_name} with {len(approved_data)} approved days...")
            success = upload_menu_to_firebase(approved_data, ru_name, use_archive)
            results[file_name] = success
            
            if success:
                try:
                    os.remove(json_file)
                    print(f"[GETTING DATA > UFSC] Arquivo removido: {file_name}")
                except Exception as e:
                    print(f"[GETTING DATA > UFSC] Erro ao remover {file_name}: {e}")
            
            # Pausa entre RUs (mesmo padrão do Ruby)
            time.sleep(2)
            
        except Exception as e:
            print(f"[GETTING DATA > UFSC] Error on {ru_name}: {e}. Skipping...")
            results[file_name] = False
    
    return results

def test_firebase_connection() -> bool:
    """
    Testa a conexão com o Firebase
    Equivalente ao teste que o UFRGS.rb faz: test_resp = firebase.get('test')
    
    Returns:
        True se a conexão foi bem-sucedida
    """
    base_url = os.environ.get('BASE_URL')
    firebase_key = os.environ.get('FIREBASE_KEY')
    
    if not base_url or not firebase_key:
        print("[FIREBASE TEST] Variáveis de ambiente não configuradas")
        return False
    
    if not requests:
        print("[FIREBASE TEST] Biblioteca requests não instalada")
        return False
    
    try:
        print(f"[FIREBASE TEST] Tentando conectar ao Firebase com URL: {base_url[:20]}...")
        
        # Fazer uma requisição de teste (equivalente ao firebase.get('test') do Ruby)
        test_url = f"{base_url}/test.json?auth={firebase_key}"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            print("[FIREBASE TEST] Conexão com Firebase estabelecida com sucesso")
            return True
        else:
            print(f"[FIREBASE TEST] Falha na conexão: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FIREBASE TEST] Erro na conexão: {e}")
        return False

if __name__ == "__main__":
    # Teste básico seguindo o padrão dos scripts Ruby
    print("=== UFSC Menu Upload Test ===")
    print("[TEST] Testando conexão com Firebase...")
    
    if test_firebase_connection():
        print("\n[TEST] Fazendo upload de cardápios aprovados...")
        print("[TEST] Usando formato UFRGS.rb (archive/menus/) - padrão para UFSC")
        
        results = upload_approved_menus(use_archive=True)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"\n[TEST] Resultado final: {success_count}/{total_count} uploads bem-sucedidos")
        
        if success_count > 0:
            print("[TEST] ✅ Upload concluído com sucesso!")
        else:
            print("[TEST] ❌ Nenhum upload foi realizado")
    else:
        print("[TEST] ❌ Não foi possível conectar ao Firebase")
        print("[TEST] Verifique as variáveis BASE_URL e FIREBASE_KEY")
