# Scraper para o RU de Florianópolis Trindade

from .base_scraper import RestaurantScraper
from bs4 import BeautifulSoup
import requests, datetime, re, io, pdfplumber

class FlorianopolisTrindadeScraper(RestaurantScraper):
    BASE_URL = "https://ru.ufsc.br/ru/"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        pdf_url = self.find_pdf_url(html, date)
        if not pdf_url:
            raise Exception("Nenhum PDF de cardápio encontrado.")
        if not pdf_url.startswith('http'):
            # Corrige links relativos
            pdf_url = requests.compat.urljoin(self.BASE_URL, pdf_url)
        pdf_bytes = self.download_pdf(pdf_url)
        text = self.extract_text_from_pdf(pdf_bytes)
        return text

# Exemplo de uso:
if __name__ == "__main__":
    scraper = FlorianopolisTrindadeScraper()
    print("Baixando e extraindo cardápio do RU Trindade...")
    try:
        menu_text = scraper.get_menu_text()
        print(menu_text)
    except Exception as e:
        print(f"Erro ao obter cardápio: {e}")
