from .base_scraper import RestaurantScraper
from bs4 import BeautifulSoup
import requests
import datetime

# Scraper para o RU de Florianópolis CCA
class FlorianopolisCCAScraper(RestaurantScraper):
    BASE_URL = "https://ru.ufsc.br/cca-2/"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        pdf_links = [a['href'] for a in links if a['href'].lower().endswith('.pdf')]
        if not pdf_links:
            raise Exception("Nenhum PDF de cardápio encontrado.")
        date = date or datetime.date.today()
        year = date.year
        week = date.isocalendar()[1]
        def link_matches(link):
            return str(year) in link and (str(week) in link or f"{date.day:02d}" in link)
        filtered = [l for l in pdf_links if link_matches(l)]
        pdf_url = filtered[0] if filtered else pdf_links[0]
        if not pdf_url.startswith('http'):
            pdf_url = requests.compat.urljoin(self.BASE_URL, pdf_url)
        pdf_bytes = self.download_pdf(pdf_url)
        return self.extract_text_from_pdf(pdf_bytes)
