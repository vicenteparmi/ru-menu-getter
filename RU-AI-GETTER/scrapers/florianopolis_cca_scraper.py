from .base_scraper import RestaurantScraper
from .pdf_menu import parse_pdf


class FlorianopolisCCAScraper(RestaurantScraper):
    BASE_URL = 'https://ru.ufsc.br/cca-2/'

    def get_menu_text(self, date=None):
        return self.current_pdf(self.BASE_URL, date)[1]

    def get_menu_data(self, date=None):
        pdf, _ = self.current_pdf(self.BASE_URL, date)
        return parse_pdf(pdf, 'cca')
