from datetime import datetime, timedelta
from check_last_menu_date import get_last_menu_date
from web_scraper import WebScraper
from ai_parse import format_menu_ai

# Configuração de execução dos scrapers por frequência
SCRAPER_FREQUENCY_CONFIG = {
    "mensal": lambda today: today.day == 1,
    "semanal": lambda today: True, # today.weekday() == 0,  # Segunda-feira
    "diario": lambda today: True
}

# Lista de scrapers configurados
SITES = [
    {
        "name": "blumenau",
        "base_url": "https://ru.blumenau.ufsc.br/cardapios/",
        "scrape_type": "image",
        "city_code": "ufsc-blu",
        "ru_name": "blumenau",
        "save_params": {"folder": "downloaded_files/blumenau"},
        "selection_mode": "last",
        "update_frequency": "semanal",
        "content_selector": "article"
    },
    {
        "name": "joinville",
        "base_url": "https://restaurante.joinville.ufsc.br/cardapio-da-semana/",
        "scrape_type": "pdf_or_image",
        "city_code": "ufsc-joi",
        "ru_name": "joinville",
        "save_params": {"folder": "downloaded_files/joinville"},
        "selection_mode": "last",
        "update_frequency": "semanal",
        "content_selector": "article"
    },
    {
        "name": "curitibanos",
        "base_url": "https://ru.curitibanos.ufsc.br/cardapio",
        "scrape_type": "pdf",
        "city_code": "ufsc-cur",
        "ru_name": "curitibanos",
        "save_params": {"folder": "downloaded_files/curitibanos"},
        "selection_mode": "first",
        "update_frequency": "mensal",
        "content_selector": "article"
    },
    {
        "name": "florianopolis_cca",
        "base_url": "https://ru.ufsc.br/cca-2/",
        "scrape_type": "pdf",
        "city_code": "ufsc-flo",
        "ru_name": "cca",
        "save_params": {"folder": "downloaded_files/florianopolis_cca"},
        "selection_mode": "first",
        "update_frequency": "semanal",
        "content_selector": "article"
    },
    {
        "name": "florianopolis_trindade",
        "base_url": "https://ru.ufsc.br/ru/",
        "scrape_type": "pdf",
        "city_code": "ufsc-flo",
        "ru_name": "trindade",
        "save_params": {"folder": "downloaded_files/florianopolis_trindade"},
        "selection_mode": "last",
        "update_frequency": "semanal",
        "content_selector": "article"
    },
]

def run_all_scrapes():
    results = {}
    today = datetime.today().date()
    for site in SITES:
        freq = site.get('update_frequency', 'diario')
        should_run = SCRAPER_FREQUENCY_CONFIG.get(freq, lambda t: True)(today)
        if not should_run:
            print(f"[SKIP] {site['ru_name']} - frequência '{freq}' não permite execução hoje ({today})")
            continue

        # Verifica a última data do cardápio no Firebase
        last_date_str = get_last_menu_date(site['ru_name'], site['city_code'], use_archive=True)
        if last_date_str:
            try:
                last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
                if last_date > today + timedelta(days=2):
                    print(f"[SKIP] {site['ru_name']} - última data ({last_date_str}) está há mais de 2 dias no futuro. Não será feito scrape.")
                    continue
            except Exception:
                print(f"[WARN] Data inválida encontrada para {site['ru_name']}: {last_date_str}")

        scraper = WebScraper(
            site['base_url'],
            site['scrape_type'],
            site['city_code'],
            site['ru_name'],
            site.get('save_params'),
            site.get('selection_mode', 'last')
        )
        print(f"[SCRAPE] Iniciando scrape para {site['ru_name']}...")
        result = scraper.scrape()
        print(f"[SCRAPE] Finalizado {site['ru_name']}: {result}")

        # Extrai conteúdo, pdfs e imagens do resultado do scrape
        content_text = result.get('text') if isinstance(result, dict) else str(result)
        pdfs = result.get('pdfs') if isinstance(result, dict) else []
        images = result.get('images') if isinstance(result, dict) else []

        # Chama a IA para formatar o cardápio
        print(f"[AI_PARSE] Formatando cardápio para {site['ru_name']}...")
        menu_json = format_menu_ai(content_text, pdf_paths=pdfs, image_paths=images)
        results[site['ru_name']] = menu_json
        print(f"[AI_PARSE] Resultado formatado {site['ru_name']}: {menu_json}")
    return results

if __name__ == "__main__":
    all_results = run_all_scrapes()
    print("[SCRAPE] Todos os resultados:")
    for ru, data in all_results.items():
        print(f"RU: {ru}")
        print(data)

    # Para debug: exibe janela se is_debug=True
    is_debug = True  # Altere para True para abrir a interface de visualização
    if is_debug:
        try:
            from debug_view import show_results_window
            show_results_window(all_results)
        except Exception as e:
            print(f"[UI] Erro ao exibir janela: {e}")
