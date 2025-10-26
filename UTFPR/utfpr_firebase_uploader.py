#!/usr/bin/env python3
"""
Firebase Uploader específico para UTFPR
Segue o padrão: /menus/utf/rus/ru-utfpr/menus/{data}
"""

import os
import json
import time
from typing import Dict, Any
import requests


def upload_utfpr_menu_to_firebase(menu_data: Dict[str, Any]) -> bool:
    """
    Faz upload de cardápio UTFPR para o Firebase.
    
    Estrutura:
    /menus/utf/rus/ru-utfpr/menus/{data}
    
    Args:
        menu_data: Dados do cardápio no formato JSON
    
    Returns:
        True se o upload foi bem-sucedido, False caso contrário
    """
    
    # Verificar variáveis de ambiente
    base_url = os.environ.get('BASE_URL')
    firebase_key = os.environ.get('FIREBASE_KEY')
    
    if not base_url or not firebase_key:
        print("[UPLOAD ERROR] Variáveis de ambiente BASE_URL e FIREBASE_KEY não configuradas")
        return False
    
    if not requests:
        print("[UPLOAD ERROR] Biblioteca requests não instalada")
        return False
    
    success_count = 0
    total_count = 0
    
    print(f"[GETTING DATA > UTFPR] Iniciando upload para Firebase...")
    
    try:
        for date_str, day_data in menu_data.items():
            # Verificar se todas as refeições estão indisponíveis
            menu = day_data.get('menu', [])
            if all(isinstance(period, list) and len(period) == 1 and period[0] == "Sem refeições disponíveis" for period in menu):
                print(f"[GETTING DATA > UTFPR] Dia {date_str} ignorado: todas as refeições indisponíveis.")
                continue
            
            total_count += 1
            
            # Obter timestamp - se for 0 ou não existir, usar timestamp atual
            timestamp = day_data.get('timestamp', 0)
            if timestamp == 0:
                timestamp = int(time.time())
            
            firebase_data = {
                'weekday': day_data.get('weekday', 'Dia não especificado'),
                'menu': day_data.get('menu', []),
                'timestamp': timestamp
            }
            
            # URL: /menus/utf/rus/ru-utfpr/menus/{date}
            firebase_path = f"archive/menus/utf/rus/ru-utfpr/menus/{date_str}"
            firebase_url = f"{base_url}/{firebase_path}.json?auth={firebase_key}"
            
            # Fazer upload (PUT request)
            response = requests.put(firebase_url, json=firebase_data, timeout=30)
            
            if response.status_code == 200:
                print(f"[GETTING DATA > UTFPR] Response: {response.status_code}. Finished for {date_str}.")
                success_count += 1
            else:
                print(f"[GETTING DATA > UTFPR] Response: {response.status_code}. Error for {date_str}.")
                print(f"[GETTING DATA > UTFPR] Error details: {response.text[:200]}...")
            
            # Pequena pausa
            time.sleep(1)
            
    except Exception as e:
        print(f"[GETTING DATA > UTFPR] Error during upload: {e}")
        return False
    
    print(f"[GETTING DATA > UTFPR] Upload summary:")
    print(f"[GETTING DATA > UTFPR] Total days: {total_count}")
    print(f"[GETTING DATA > UTFPR] Successful uploads: {success_count}")
    print(f"[GETTING DATA > UTFPR] Failures: {total_count - success_count}")
    
    return success_count > 0
