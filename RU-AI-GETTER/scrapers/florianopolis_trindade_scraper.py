# Scraper para o RU de Florianópolis Trindade

from .base_scraper import RestaurantScraper
from bs4 import BeautifulSoup, Tag
import requests, datetime, re, io, pdfplumber
from urllib.parse import urljoin

class FlorianopolisTrindadeScraper(RestaurantScraper):
    BASE_URL = "https://ru.ufsc.br/ru/"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        meses = []
        for strong in soup.find_all('strong'):
            mes_nome = strong.get_text(strip=True)
            if not mes_nome.lower().startswith('mês de'):
                continue
            p = strong.parent
            if not isinstance(p, Tag):
                continue
            ul = None
            next_sibling = p.next_sibling
            while next_sibling:
                if isinstance(next_sibling, Tag) and next_sibling.name == 'ul':
                    ul = next_sibling
                    break
                next_sibling = next_sibling.next_sibling
            if ul:
                links = []
                for li in ul.children:
                    if isinstance(li, Tag) and li.name == 'li':
                        for a in li.children:
                            if isinstance(a, Tag) and a.name == 'a':
                                href = a.get('href')
                                if isinstance(href, str) and href.lower().endswith('.pdf'):
                                    links.append(href)
                if links:
                    meses.append((mes_nome, links))
        if not meses:
            raise Exception("Nenhuma lista de cardápios mensal encontrada.")
        mes_mais_recente, links_mais_recentes = meses[-1]
        pdf_url = links_mais_recentes[-1]
        if not pdf_url.startswith('http'):
            pdf_url = urljoin(self.BASE_URL, pdf_url)
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
