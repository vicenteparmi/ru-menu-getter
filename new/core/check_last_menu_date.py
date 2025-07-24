import env_config
def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except Exception:
        return False

def get_last_menu_date(ru_name, city_code, use_archive=True):
    BASE_URL = getattr(env_config, 'BASE_URL', None)
    FIREBASE_KEY = getattr(env_config, 'FIREBASE_KEY', None)
    if not BASE_URL or not FIREBASE_KEY:
        print("[ERROR] Variáveis BASE_URL e FIREBASE_KEY não configuradas")
        return None
    if use_archive:
        firebase_path = f"archive/menus/{city_code}/rus/{ru_name}/menus.json"
    else:
        firebase_path = f"menus/{city_code}/rus/{ru_name}/menus.json"
    firebase_url = f"{BASE_URL}/{firebase_path}?auth={FIREBASE_KEY}"
    try:
        resp = requests.get(firebase_url, timeout=30)
        if resp.status_code != 200:
            print(f"[ERROR] Falha ao buscar menus de {ru_name}: {resp.status_code}")
            return None
        data = resp.json()
        if not data:
            return None
        dates = [d for d in data.keys() if is_valid_date(d)]
        if not dates:
            return None
        last_date = sorted(dates)[-1]
        return last_date
    except Exception as e:
        print(f"[ERROR] Falha ao buscar menus de {ru_name}: {e}")
        return None
import os
import requests
from datetime import datetime

# Carrega variáveis do .env se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_URL = os.environ.get('BASE_URL')
FIREBASE_KEY = os.environ.get('FIREBASE_KEY')

UFSC_MAPPING = {
    'blumenau': 'ufsc-blu',
    'curitibanos': 'ufsc-cur',
    'cca': 'ufsc-flo',
    'trindade': 'ufsc-flo',
    'joinville': 'ufsc-joi'
}


