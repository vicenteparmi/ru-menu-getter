import datetime as dt
import re
import sys
from urllib.parse import unquote, urljoin

import pdfplumber
from bs4 import BeautifulSoup

from .base_scraper import RestaurantScraper
from .pdf_menu import clean, payload


MONTHS = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
          'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


def monthly_menu(pdf, month):
    result = {}
    short_month = MONTHS[month.month - 1][:3]
    with pdfplumber.open(pdf) as document:
        for page in document.pages:
            for table in page.extract_tables():
                dates = None
                vegetarian = False
                for row in table:
                    if len(row) != 7:
                        continue
                    matches = [re.fullmatch(rf'(\d{{1,2}})/{short_month}', clean(cell), re.I) for cell in row]
                    if any(matches):
                        dates = [month.replace(day=int(m[1])) if m else None for m in matches]
                        if any(day and day.weekday() != index for index, day in enumerate(dates)):
                            raise ValueError('Datas divergentes nas colunas de Curitibanos')
                        for day in filter(None, dates):
                            if day in result:
                                raise ValueError(f'Data duplicada em Curitibanos: {day}')
                            result[day] = []
                        continue
                    if dates and clean(row[0]).upper().startswith(('OBS:', 'NUTRICIONISTA', 'CARDÁPIO')):
                        dates = None
                    if not dates:
                        continue
                    if clean(row[0]) == 'BEBIDA: ÁGUA':
                        for day in filter(None, dates):
                            result[day].append('Bebida: água')
                        continue
                    if row[1:] == [None] * 6:
                        vegetarian = clean(row[0]) == 'OPÇÃO VEGETARIANA'
                        continue
                    if vegetarian and any(day and cell is None for day, cell in zip(dates, row)):
                        print('Curitibanos: linha vegetariana com colunas sobrepostas, omitida', file=sys.stderr)
                        continue
                    for day, cell in zip(dates, row):
                        if day and clean(cell):
                            result[day].append(clean(cell))
    return {day.isoformat(): payload(day, [[], items, items.copy()])
            for day, items in result.items() if len(items) >= 5 and 'Arroz' in items}


class CuritibanosScraper(RestaurantScraper):
    BASE_URL = 'https://ru.curitibanos.ufsc.br/cardapio'

    def menu_pdf(self, date):
        soup = BeautifulSoup(self.fetch_html(self.BASE_URL), 'html.parser')
        month = MONTHS[date.month - 1]
        for anchor in soup.select('a[href]'):
            link = unquote(anchor['href']).lower()
            label = anchor.get_text(' ', strip=True).lower()
            if link.endswith('.pdf') and (
                re.search(rf'{month}\s+de\s+{date.year}\b', label)
                or re.search(rf'{month}[-_ ]{date.year}\b', link)
            ):
                return self.download_pdf(urljoin(self.BASE_URL, anchor['href']))
        raise ValueError(f'Curitibanos: PDF mensal ausente para {date:%Y-%m}')

    def get_menu_text(self, date=None):
        return self.extract_text_from_pdf(self.menu_pdf(date or dt.date.today()))

    def get_menu_data(self, date=None):
        date = date or dt.date.today()
        return monthly_menu(self.menu_pdf(date), date.replace(day=1))
