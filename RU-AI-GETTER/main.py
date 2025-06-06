# Arquivo principal para orquestrar a coleta e processamento de dados dos RUs.

# --- Bloco para garantir ambiente virtual e dependências essenciais ---
import sys
import subprocess
import os

venv_path = os.path.join(os.path.dirname(__file__), '.venv')
activate_path = os.path.join(venv_path, 'bin', 'activate_this.py')

# Cria o ambiente virtual se não existir
if not os.path.isdir(venv_path):
    print('[INFO] Criando ambiente virtual (.venv)...')
    subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)

# Ativa o ambiente virtual (para scripts Python)
if os.environ.get('VIRTUAL_ENV') != venv_path:
    activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
    if os.path.exists(activate_this):
        with open(activate_path) as f:
            exec(f.read(), {'__file__': activate_this})

# Garante que o pacote requests está instalado
try:
    import requests
except ImportError:
    print('[INFO] Instalando pacote requests...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
# --- Fim do bloco ambiente virtual ---

import json
from datetime import datetime

from scrapers import (
    BlumenauScraper,
    CuritibanosScraper,
    FlorianopolisCCAScraper,
    FlorianopolisTrindadeScraper,
    JoinvilleScraper,
)
from core.postprocess import clean_menu_text, extract_dates_and_weekdays, associate_dates_weekdays
from core.ai_parse import parse_menu_with_ollama

# Definição global das funções de log
def success(x): return x
def warning(x): return x
def error(x): return x
def info(x): return x
def highlight(x): return x

# Tenta importar versões coloridas, mas sempre mantém as funções globais
try:
    from core.colorlog_util import success, warning, error, info, highlight
except ImportError:
    pass  # Usa as funções simples definidas acima

# Adiciona import para Gemini
try:
    from google.generativeai import GenerativeModel
    import google.generativeai as genai
except ImportError:
    GenerativeModel = None
    genai = None

# Carrega variáveis do .env automaticamente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Gemini: função de parsing via Google AI

def parse_menu_with_gemini(text: str, model: str = "gemini-pro", api_key: str = None, image_path: str = None) -> dict:
    """
    Envia o texto (e opcionalmente uma imagem) do cardápio para a API Gemini e retorna o JSON estruturado.
    """
    import os
    import json
    try:
        import importlib
        genai = importlib.import_module("google.generativeai")
    except ImportError:
        raise ImportError("google-generativeai não está instalado. Instale com 'pip install google-generativeai'.")
    
    # Importar validador JSON
    try:
        from core.json_validator import extract_and_validate_json, create_json_schema, create_fallback_response
    except ImportError:
        print("[AVISO] json_validator não encontrado, usando método básico")
        extract_and_validate_json = None
        create_fallback_response = None
    
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não definido. Configure no .env ou variável de ambiente.")
    
    genai.configure(api_key=api_key)
    
    # Prompt melhorado com instruções mais claras
    prompt = (
        "Você deve extrair e estruturar as informações de cardápio do restaurante universitário em formato JSON. "
        "Siga EXATAMENTE o formato especificado abaixo.\n\n"
        
        "REGRAS IMPORTANTES:\n"
        "1. Use APENAS o formato YYYY-MM-DD para datas\n"
        "2. Cada dia deve ter: menu (array de arrays), timestamp (sempre 0), weekday (dia da semana em português)\n"
        "3. O array 'menu' representa as refeições: [café da manhã/lanche, almoço, jantar]\n"
        "4. Se não houver informação para uma refeição, use EXATAMENTE ['Sem refeições disponíveis']\n"
        "5. Capitalize adequadamente os nomes dos pratos\n"
        "6. Mantenha opções vegetarianas/veganas quando presentes\n"
        "7. Inclua acompanhamentos e saladas quando mencionados\n\n"
        
        "FORMATO DE SAÍDA (JSON válido, sem comentários):\n"
        "{\n"
        '  "2025-06-05": {\n'
        '    "menu": [\n'
        '      ["Sem refeições disponíveis"],\n'
        '      ["Bife acebolado", "Opção vegana: hambúrguer de feijão", "Arroz", "Feijão", "Salada verde"],\n'
        '      ["Frango grelhado", "Opção vegetariana: lasanha de berinjela", "Purê de batata", "Salada mista"]\n'
        '    ],\n'
        '    "timestamp": 0,\n'
        '    "weekday": "Quinta-Feira"\n'
        '  }\n'
        "}\n\n"
        
        "TEXTO DO CARDÁPIO A SER PROCESSADO:\n" + text + "\n\n"
        
        "Retorne APENAS o JSON válido, sem texto adicional:"
    )
    
    # Configurar modelo com parâmetros otimizados
    generation_config = {
        "temperature": 0.1,  # Baixa temperatura para mais consistência
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    
    model_obj = genai.GenerativeModel(
        model_name=model,
        generation_config=generation_config
    )
    
    try:
        if image_path:
            try:
                import importlib
                pil = importlib.import_module("PIL.Image")
            except ImportError:
                raise ImportError("Pillow não está instalado. Instale com 'pip install pillow'.")
            img = pil.open(image_path)
            response = model_obj.generate_content([prompt, img])
        else:
            response = model_obj.generate_content(prompt)
        
        result = response.text
        print(f"[DEBUG] Resposta do Gemini: {result[:500]}...")
        
        # Usar validador se disponível
        if extract_and_validate_json:
            return extract_and_validate_json(result)
        else:
            # Método básico de fallback
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("Nenhum JSON encontrado na resposta")
            json_str = result[json_start:json_end]
            return json.loads(json_str)
            
    except Exception as e:
        print(f"[ERRO] Falha no parsing com Gemini: {e}")
        if extract_and_validate_json:
            from core.json_validator import create_fallback_response
            return create_fallback_response()
        else:
            raise ValueError(f"Falha ao extrair JSON da resposta do Gemini: {e}\nResposta: {result}")

def parse_blumenau_table(menu_clean: str) -> dict:
    """
    Faz o parsing do texto tabular do cardápio de Blumenau e retorna um dicionário {data: texto_do_dia}
    """
    import re
    lines = menu_clean.splitlines()
    # Encontrar linha dos dias e das datas
    dias_idx = None
    datas_idx = None
    for i, line in enumerate(lines):
        if re.search(r"segunda.*terça.*quarta.*quinta.*sexta.*s[áa]bado.*domingo", line, re.IGNORECASE):
            dias_idx = i
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}.*\d{1,2}/\d{1,2}/\d{4}", line):
            datas_idx = i
    if dias_idx is None or datas_idx is None:
        return {}
    dias = re.split(r"\s+", lines[dias_idx].strip())
    datas = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", lines[datas_idx])
    # Coletar colunas (ajuste: dividir cada linha em N partes iguais, onde N = len(datas))
    colunas = [[] for _ in datas]
    print("[DEBUG] Linhas após datas (OCR):")
    for line in lines[datas_idx+1:]:
        print(line)
        if not line.strip():
            continue
        palavras = line.strip().split()
        if len(palavras) >= len(datas):
            tam = len(palavras) // len(datas)
            resto = len(palavras) % len(datas)
            idx = 0
            for i in range(len(datas)):
                extra = 1 if i < resto else 0
                fim = idx + tam + extra
                colunas[i].append(' '.join(palavras[idx:fim]))
                idx = fim
        else:
            # Se não houver palavras suficientes, adiciona vazio
            for i in range(len(datas)):
                colunas[i].append('')
    # Montar texto por dia
    blocos = {}
    for i, data in enumerate(datas):
        bloco = []
        for j, line in enumerate(lines[dias_idx:datas_idx+1]):
            if j == 0:
                bloco.append(f"Dia: {dias[i]} - Data: {data}")
            else:
                bloco.append(line)
        for item in colunas[i]:
            bloco.append(item)
        blocos[data] = "\n".join(bloco)
    return blocos

LAST_RUNS_FILE = os.path.join(os.path.dirname(__file__), "last_runs.json")

def load_last_runs():
    if os.path.exists(LAST_RUNS_FILE):
        try:
            with open(LAST_RUNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_last_run(ru_nome):
    last_runs = load_last_runs()
    last_runs[ru_nome] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LAST_RUNS_FILE, "w", encoding="utf-8") as f:
        json.dump(last_runs, f, ensure_ascii=False, indent=2)

def prompt_user_options():
    print("\n=== Configuração de Parsing dos Cardápios ===")
    last_runs = load_last_runs()
    # Escolha do método
    while True:
        metodo = input("Escolha o método de parsing (1=Ollama, 2=Google Gemini, q=abandonar): ").strip().lower()
        if metodo == "q":
            print("Operação cancelada pelo usuário.")
            exit(0)
        if metodo in ("1", "2"): break
        print("Opção inválida. Digite 1, 2 ou q.")
    metodo = "ollama" if metodo == "1" else "gemini"
    # Modelos pré-definidos para Gemini
    gemini_modelos = [
        "gemma-3-27b-it",
        "gemma-3-12b-it",
        "gemma-3-4b-it",
    ]
    if metodo == "gemini":
        print("\nModelos Gemini disponíveis:")
        for i, m in enumerate(gemini_modelos, 1):
            print(f"  {i}. {m}")
        while True:
            modelo_idx = input(f"Escolha o modelo Gemini (1-{len(gemini_modelos)}), ou digite o nome, ou q para abandonar: ").strip().lower()
            if modelo_idx == "q":
                print("Operação cancelada pelo usuário.")
                exit(0)
            if modelo_idx.isdigit() and 1 <= int(modelo_idx) <= len(gemini_modelos):
                modelo = gemini_modelos[int(modelo_idx)-1]
                break
            elif modelo_idx:
                modelo = modelo_idx
                break
            else:
                print("Seleção inválida.")
    else:
        modelo = input("Informe o modelo a ser usado (ex: ollama/llama3) ou q para abandonar: ").strip()
        if modelo.lower() == "q":
            print("Operação cancelada pelo usuário.")
            exit(0)
        modelo = modelo or "llama3"
    # API key se Gemini
    api_key = None
    if metodo == "gemini":
        api_key = input("Informe sua GEMINI_API_KEY (ou deixe em branco para usar variável de ambiente, ou q para abandonar): ").strip()
        if api_key.lower() == "q":
            print("Operação cancelada pelo usuário.")
            exit(0)
        api_key = api_key or None
    # Seleção dos RUs
    rus_disponiveis = [
        ("Blumenau", BlumenauScraper),
        ("Curitibanos", CuritibanosScraper),
        ("Florianópolis CCA", FlorianopolisCCAScraper),
        ("Florianópolis Trindade", FlorianopolisTrindadeScraper),
        ("Joinville", JoinvilleScraper),
    ]
    print("\nSelecione os RUs a serem processados (ex: 1,3,5 ou q para abandonar):")
    for i, (nome, _) in enumerate(rus_disponiveis, 1):
        data = last_runs.get(nome, "nunca")
        print(f"  {i}. {nome} (Última atualização: {data})")
    print(f"  0. Todos ({', '.join([n for n, _ in rus_disponiveis])})")
    while True:
        sel = input("Digite os números separados por vírgula: ").strip().lower()
        if sel == "q":
            print("Operação cancelada pelo usuário.")
            exit(0)
        if sel == "0":
            # Nova lógica: permitir excluir alguns RUs
            print("Você selecionou TODOS os RUs.")
            excluir = input("Deseja excluir algum RU? (Digite os números separados por vírgula, ou pressione Enter para continuar com todos): ").strip().lower()
            if excluir:
                try:
                    idxs_excluir = [int(x)-1 for x in excluir.split(",") if x.strip().isdigit() and 0 < int(x) <= len(rus_disponiveis)]
                    rus_escolhidos = [ru for i, ru in enumerate(rus_disponiveis) if i not in idxs_excluir]
                    if not rus_escolhidos:
                        print("Nenhum RU selecionado. Selecione pelo menos um.")
                        continue
                except Exception:
                    print("Seleção inválida.")
                    continue
            else:
                rus_escolhidos = rus_disponiveis
            break
        try:
            idxs = [int(x)-1 for x in sel.split(",") if x.strip().isdigit() and 0 < int(x) <= len(rus_disponiveis)]
            if idxs:
                rus_escolhidos = [rus_disponiveis[i] for i in idxs]
                break
        except Exception: pass
        print("Seleção inválida.")
    return metodo, modelo, api_key, rus_escolhidos

def run_all_scrapers_interactive():
    # Referências explícitas às funções globais para evitar problemas de escopo
    global success, warning, error, info, highlight
    
    metodo, modelo, api_key, rus_escolhidos = prompt_user_options()
    print(highlight("\n⏳ Coletando cardápios dos restaurantes selecionados..."))
    # Importar validador
    try:
        from core.json_validator import comprehensive_json_validator, NO_MEALS_TEXT
        use_validator = True
        print(success("[INFO] Validador JSON carregado com sucesso"))
    except ImportError:
        use_validator = False
        print(warning("[AVISO] Validador JSON não disponível"))
    resultados = {}
    for nome, ScraperClass in rus_escolhidos:
        scraper = ScraperClass()
        try:
            print(highlight(f"\n===== {nome} ====="))
            print(info("Obtendo texto do cardápio..."))
            menu = scraper.get_menu_text()
            menu_clean = clean_menu_text(menu)
            print(info("Texto limpo obtido (mostrando primeiras 3 linhas):"))
            preview = '\n'.join(menu_clean.splitlines()[:3])
            print(preview + ("\n..." if len(menu_clean.splitlines()) > 3 else ""))
            # Parsing
            if metodo == "ollama":
                print(info("Enviando para o Ollama..."))
                image_path = getattr(scraper, 'get_menu_image_path', lambda: None)()
                parsed = parse_menu_with_ollama(menu_clean, model=modelo, image_path=image_path)
            else:
                print(info("Enviando para o Gemini..."))
                image_path = getattr(scraper, 'get_menu_image_path', lambda: None)()
                parsed = parse_menu_with_gemini(menu_clean, model=modelo, api_key=api_key, image_path=image_path)
            # Validação
            if use_validator:
                print(info("[VALIDAÇÃO] Verificando formato do JSON..."))
                is_valid, validated_json, errors = comprehensive_json_validator(parsed)
                if is_valid:
                    print(success("[VALIDAÇÃO] JSON válido!"))
                    parsed = validated_json
                else:
                    print(warning(f"[VALIDAÇÃO] {len(errors)} problema(s) encontrado(s):"))
                    for err in errors[:5]:
                        print(error(f"   - {err}"))
                    if len(errors) > 5:
                        print(warning(f"   ... e mais {len(errors) - 5} erros"))
                    parsed = validated_json
                    print(warning("[VALIDAÇÃO] Usando JSON corrigido automaticamente"))
            print(info("[IA] JSON final salvo (primeiras 5 linhas):"))
            json_preview = json.dumps(parsed, ensure_ascii=False, indent=2).splitlines()[:5]
            print('\n'.join(json_preview) + ("\n..." if len(json_preview) == 5 else ""))
            # Salva o JSON
            os.makedirs(os.path.join(os.path.dirname(__file__), "jsons"), exist_ok=True)
            json_path = os.path.join(os.path.dirname(__file__), "jsons", f"{nome.lower().replace(' ', '_')}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            print(success(f"[SALVO] JSON salvo em {json_path}"))
            save_last_run(nome)
            resultados[nome] = parsed
        except Exception as e:
            print(error(f"[ERRO] {e}"))
            resultados[nome] = None
    # Validação automática de todos os arquivos JSON salvos
    import glob
    from core.json_validator import comprehensive_json_validator, NO_MEALS_TEXT
    jsons_dir = os.path.join(os.path.dirname(__file__), "jsons")
    json_files = glob.glob(os.path.join(jsons_dir, "*.json"))
    print(highlight("\n[VALIDAÇÃO FINAL] Verificando todos os arquivos JSON salvos..."))
    algum_erro = False
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        is_valid, processed, errors = comprehensive_json_validator(data)
        if is_valid:
            print(success(f"✅ {os.path.basename(jf)}: JSON válido e padronizado!"))
        else:
            algum_erro = True
            print(error(f"❌ {os.path.basename(jf)}: {len(errors)} erro(s) encontrado(s):"))
            for err in errors:
                print(error(f"   - {err}"))
        # Checagem extra: garantir que só existe 'Sem refeições disponíveis' padronizado
        for dia, day_info in processed.items():
            for refeicao in day_info.get('menu', []):
                for item in refeicao:
                    if any(p in item.lower() for p in ['sem', 'não', 'indisponível', 'cardapio', 'menu']) and item != NO_MEALS_TEXT:
                        print(warning(f"   ⚠️  Atenção: '{item}' não está padronizado em {os.path.basename(jf)} ({dia})"))
                        algum_erro = True
    if not algum_erro:
        print(success("\n🏆 Todos os arquivos JSON passaram na validação final!"))
    else:
        print(warning("\n⚠️  Corrija os erros acima para garantir padronização total!"))
    
    # Abrir GUI de revisão após validação
    print(highlight("\n[GUI] Abrindo interface de revisão dos cardápios..."))
    try:
        import webbrowser
        import threading
        import time
        import socket
        def find_free_port(preferred_ports):
            for port in preferred_ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(("127.0.0.1", port))
                        return port
                    except OSError:
                        continue
            raise RuntimeError("Nenhuma porta disponível para o servidor web.")

        def start_web_gui(port):
            from interface.menu_review_web import app
            print(f"Acesse: http://localhost:{port}")
            # Rodar sem debug para evitar erro de signal em thread secundária
            app.run(debug=False, host='0.0.0.0', port=port)
        port = find_free_port([8080, 8081, 8082])
        thread = threading.Thread(target=start_web_gui, args=(port,))
        thread.daemon = False  # Não usar daemon para manter o processo vivo
        thread.start()
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}")
        thread.join()  # Aguarda o término do servidor Flask
    except Exception as e:
        print(error(f"[ERRO] Falha ao abrir interface web: {e}"))
        print(info("[GUI] Execute 'python menu_review_web.py' para abrir manualmente"))
    return resultados

if __name__ == "__main__":
    print("Iniciando o processo de coleta de dados dos RUs...")
    run_all_scrapers_interactive()
