from .base_scraper import RestaurantScraper
from bs4 import BeautifulSoup
import requests, datetime, io
from PIL import Image
import pytesseract

# Scraper para o RU de Joinville
class JoinvilleScraper(RestaurantScraper):
    BASE_URL = "https://restaurante.joinville.ufsc.br/cardapio-da-semana/"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        # Tenta PDF primeiro
        links = soup.find_all('a', href=True)
        pdf_links = [a['href'] for a in links if a['href'].lower().endswith('.pdf')]
        if pdf_links:
            pdf_url = pdf_links[0]
            if not pdf_url.startswith('http'):
                pdf_url = requests.compat.urljoin(self.BASE_URL, pdf_url)
            pdf_bytes = self.download_pdf(pdf_url)
            return self.extract_text_from_pdf(pdf_bytes)
        # Senão, usa OCR na imagem
        img_tag = soup.find('img')
        if not img_tag or not img_tag.get('src'):
            raise Exception("Nenhum cardápio encontrado (PDF ou imagem)")
        img_url = img_tag['src']
        if not img_url.startswith('http'):
            img_url = requests.compat.urljoin(self.BASE_URL, img_url)
        resp = requests.get(img_url)
        resp.raise_for_status()
        image = Image.open(io.BytesIO(resp.content))
        return pytesseract.image_to_string(image, lang='por')
