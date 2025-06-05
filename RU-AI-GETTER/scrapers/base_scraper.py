import requests
from bs4 import BeautifulSoup
import pdfplumber
import datetime
import re
import io

class RestaurantScraper:
    """
    Classe base para scrapers de restaurantes. Permite fácil extensão para novos restaurantes.
    """
    def fetch_html(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def find_pdf_url(self, html, date=None):
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        pdf_links = [a['href'] for a in links if a['href'].lower().endswith('.pdf')]
        if not pdf_links:
            return None
        if date is None:
            date = datetime.date.today()

        def extract_date_from_link(link):
            match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', link)
            if match:
                try:
                    parts = re.split(r'[./-]', match.group(1))
                    if len(parts[-1]) == 2:
                        parts[-1] = '20' + parts[-1]
                    return datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                except Exception:
                    return None
            return None

        pdf_links_with_dates = [(link, extract_date_from_link(link)) for link in pdf_links]
        pdf_links_with_dates = [x for x in pdf_links_with_dates if x[1] is not None]
        if not pdf_links_with_dates:
            return pdf_links[0]
        pdf_links_with_dates.sort(key=lambda x: abs((x[1] - date).days))
        return pdf_links_with_dates[0][0]

    def download_pdf(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return io.BytesIO(resp.content)

    def extract_text_from_pdf(self, pdf_bytes):
        with pdfplumber.open(pdf_bytes) as pdf:
            text = "\n".join(page.extract_text() or '' for page in pdf.pages)
        return text
