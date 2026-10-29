from .base_scraper import RestaurantScraper
from .pdf_menu import parse_pdf


class JoinvilleScraper(RestaurantScraper):
    BASE_URL = 'https://restaurante.joinville.ufsc.br/cardapio-da-semana/'

    def get_menu_text(self, date=None):
        return self.current_pdf(self.BASE_URL, date)[1]

    def get_menu_data(self, date=None):
        pdf, _ = self.current_pdf(self.BASE_URL, date)
        return parse_pdf(pdf, 'joinville')
