import datetime as dt
import re
from urllib.parse import urljoin

import pdfplumber
from bs4 import BeautifulSoup

from .base_scraper import RestaurantScraper
from .pdf_menu import clean, dates_in_text, payload


def daily_rows(pdf):
    with pdfplumber.open(pdf) as document:
        rows = document.pages[0].extract_table() or []
    result = {}
    for row in rows:
        dates = dates_in_text(clean(row[0]))
        if not dates:
            continue
        items = [clean(line) for line in (row[1] or '').splitlines() if clean(line)]
        if len(dates) != 1 or not items or dates[0] in result:
            raise ValueError('Linha diária inesperada no PDF de Trindade')
        result[dates[0]] = items
    return result


def lunch_and_dinner(items):
    lunch, dinner = [], []
    for item in items:
        if re.search(r'\((almoço|jantar)\)', item, re.I):
            match = re.fullmatch(r'(.*?)(?:\s*\(almoço\)\s*/\s*)(.*?)\s*\(jantar\)', item, re.I)
            if not match:
                raise ValueError('Separação de almoço e jantar inesperada em Trindade')
            lunch.append(match[1])
            label, separator, _ = match[1].partition(':')
            dinner.append(f'{label}: {match[2]}' if separator else match[2])
        else:
            lunch.append(item)
            dinner.append(item)
    return lunch, dinner


class FlorianopolisTrindadeScraper(RestaurantScraper):
    BASE_URL = 'https://ru.ufsc.br/ru/'

    def current_tables(self, date):
        soup = BeautifulSoup(self.fetch_html(self.BASE_URL), 'html.parser')
        tables = {}
        for anchor in reversed(soup.select('a[href]')):
            if not anchor['href'].lower().endswith('.pdf'):
                continue
            label = anchor.get_text(' ', strip=True).lower()
            period = 'café' if 'café' in label else 'principal'
            if 'cardápio' not in label or period in tables:
                continue
            ends = re.findall(r'(\d{1,2})[./](\d{2})(?!\d)', label)
            if not ends:
                continue
            end_day, end_month = ends[-1]
            if not any((date + dt.timedelta(days=n)).strftime('%d/%m') == f'{int(end_day):02d}/{end_month}'
                       for n in range(7)):
                continue
            pdf = self.download_pdf(urljoin(self.BASE_URL, anchor['href']))
            rows = daily_rows(pdf)
            if date in rows or (period == 'café' and date.weekday() >= 5
                                and date - dt.timedelta(days=date.weekday()) in rows):
                tables[period] = rows
            if len(tables) == 2:
                break
        return tables

    def get_menu_data(self, date=None):
        date = date or dt.date.today()
        tables = self.current_tables(date)
        if 'principal' not in tables or (date.weekday() < 5 and 'café' not in tables):
            raise ValueError(f'Trindade: PDF de refeições ausente para {date}')
        result = {}
        for day, items in tables['principal'].items():
            breakfast = tables.get('café', {}).get(day, [])
            if breakfast:
                breakfast = [item for item in breakfast if item not in ('PÃES', 'COMPLEMENTOS:')]
                breakfast.append('Exclusivo para estudantes isentos')
            result[day.isoformat()] = payload(day, [breakfast, *lunch_and_dinner(items)])
        return result

    def get_menu_text(self, date=None):
        return '\n'.join(f"{day}: {data['menu']}" for day, data in self.get_menu_data(date).items())
