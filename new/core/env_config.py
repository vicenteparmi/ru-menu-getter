import os
from pathlib import Path

# Tenta carregar variáveis do .env se existir
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        print('[ENV_CONFIG] python-dotenv não instalado. Instale com "pip install python-dotenv" para usar .env.')

# Se não houver .env, define valores padrão (opcional)
os.environ.setdefault('BASE_URL', 'https://seu-endereco-do-firebase.firebaseio.com')
os.environ.setdefault('FIREBASE_KEY', 'sua-chave-do-firebase')
os.environ.setdefault('GEMINI_API_KEY', 'sua-chave-do-gemini')

