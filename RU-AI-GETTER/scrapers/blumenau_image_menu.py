"""Read the official Blumenau weekly image, checking the dates and table layout."""
import datetime as dt
import io
import re
import subprocess
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

from .pdf_menu import WEEKDAYS, payload


def read_image(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as image:
        return image.convert('RGB')


def ocr(image, box, mode=6):
    width, height = image.size
    region = image.crop(tuple(round(value * size) for value, size in zip(box, (width, height) * 2)))
    gray = ImageOps.autocontrast(ImageOps.grayscale(region))
    enlarged = gray.resize((gray.width * 3, gray.height * 3), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    enlarged.save(buffer, format='PNG')
    result = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', 'por', '--psm', str(mode)],
                            input=buffer.getvalue(), capture_output=True, check=True, timeout=25)
    return [line.strip(' |') for line in result.stdout.decode().splitlines() if line.strip(' |')]


def parse_week(image, date, breakfast):
    header = ' '.join(ocr(image, (.18, .078, .998, .111), 7))
    match = re.search(r'(\d{2}/\d{2})\s+a\s+(\d{2}/\d{2}/\d{4})', header)
    if not match:
        raise ValueError('Blumenau: intervalo semanal ilegível')
    end = dt.datetime.strptime(match[2], '%d/%m/%Y').date()
    start = end - dt.timedelta(days=4)
    if start.strftime('%d/%m') != match[1] or start.weekday() != 0 or not start <= date <= end:
        raise ValueError(f'Blumenau: imagem de {start} a {end} fora da semana solicitada')

    result = {}
    for column in range(5):
        day = start + dt.timedelta(days=column)
        left, right = (.178, .346, .514, .677, .843, 1)[column:column + 2]
        heading = ' '.join(ocr(image, (left, .115, right, .151), 7))
        if heading.casefold() != WEEKDAYS[column].split('-')[0].casefold():
            raise ValueError(f'Blumenau: coluna inesperada para {day}')
        bands = ((.151, .197), (.197, .275), (.275, .307),
                 (.307, .402), (.402, .429), (.429, .457))
        sections = [ocr(image, (left + .005, top, right - .005, bottom))
                    for top, bottom in bands]
        main, sides, garnish, salads, vegetarian, dessert = sections
        if not all(sections):
            raise ValueError(f'Blumenau: seção ilegível na coluna de {day}')
        if salads[-1].casefold() == 'agridoce' and len(salads) > 1:
            salads[-2:] = [' '.join(salads[-2:])]
        main_dish = re.sub(r'\bCame moída\b', 'Carne moída', ' '.join(main))
        main_dish = re.sub(r'\blarania\b', 'laranja', main_dish)
        items = [main_dish, *sides, ' '.join(garnish), *salads,
                 ' '.join(vegetarian), ' '.join(dessert)]
        if len(items) < 8 or not any('arroz integral' in item.casefold() for item in items):
            raise ValueError(f'Blumenau: itens insuficientes na coluna de {day}')
        result[day.isoformat()] = payload(day, [breakfast, items, items.copy()])
    return result


def collect(scraper, date):
    # On weekends, use the same week's publication. The source lists weekdays only.
    reference = date - dt.timedelta(days=max(0, date.weekday() - 4))
    soup = BeautifulSoup(scraper.fetch_html(scraper.BASE_URL), 'html.parser')
    images = soup.select('article img[src]')
    sources = {}
    for image in images:
        source = urljoin(scraper.BASE_URL, image['src'])
        name = source.rsplit('/', 1)[-1].lower()
        for key in ('cardapio', 'cafedamanha'):
            if name.startswith(key):
                sources.setdefault(key, source.replace('http://', 'https://', 1))
    if set(sources) != {'cardapio', 'cafedamanha'}:
        raise ValueError('Blumenau: cardápio semanal ou de café ausente')
    breakfast = ocr(read_image(sources['cafedamanha']), (.015, .19, .58, .992))
    if len(breakfast) != 9 or not {'café', 'chá', 'fruta'} <= {item.casefold() for item in breakfast}:
        raise ValueError('Blumenau: estrutura do café da manhã inesperada')
    if breakfast[2].lower().endswith(' ou'):
        breakfast[2:4] = [' '.join(breakfast[2:4])]
    return parse_week(read_image(sources['cardapio']), reference, breakfast)
