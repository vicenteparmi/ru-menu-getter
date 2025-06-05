# Scraper para o RU de Curitibanos

from .base_scraper import RestaurantScraper
from bs4 import BeautifulSoup
import requests, datetime

class CuritibanosScraper(RestaurantScraper):
    BASE_URL = "https://ru.curitibanos.ufsc.br/cardapio"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        pdf_links = [a['href'] for a in links if a['href'].lower().endswith('.pdf')]
        if not pdf_links:
            raise Exception("Nenhum PDF de cardápio encontrado.")
        if date is None:
            date = datetime.date.today()
        month = date.month
        year = date.year
        def link_matches_month(link):
            return (str(month).zfill(2) in link or date.strftime('%B').lower() in link.lower()) and str(year) in link
        filtered = [l for l in pdf_links if link_matches_month(l)]
        pdf_url = filtered[0] if filtered else pdf_links[0]
        if not pdf_url.startswith('http'):
            pdf_url = requests.compat.urljoin(self.BASE_URL, pdf_url)
        pdf_bytes = self.download_pdf(pdf_url)
        text = self.extract_text_from_pdf(pdf_bytes)
        return text
