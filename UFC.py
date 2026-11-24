#!/usr/bin/env python3
"""Collect UFC Fortaleza's public HTML menus and publish them to CampusDine."""
import argparse
import datetime as dt
import json
import os
import time
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from UFV import Firebase, NO_MEALS, WEEKDAYS

SOURCE = 'https://ufc2012.ufc.br/restaurante/cardapio/1-restaurante-universitario-de-fortaleza'
CITY = 'menus/ufc-for'
RESTAURANT = f'{CITY}/rus/ru-ufc'
METADATA = {
    f'{CITY}/name': 'Fortaleza, Ceará',
    f'{CITY}/university': 'UFC',
    **{
        f'{RESTAURANT}/{field}': value
        for field, value in {
            'name': 'Restaurante Universitário',
            'address': 'Refeitórios da UFC - Fortaleza, CE',
            'url': SOURCE,
            'displayMessage': False,
            'isNew': True,
            'status': 'beta',
            'updateFrequency': 'daily',
            'updateModeIsAuto': True,
        }.items()
    },
}


def parse_day(html, day):
    page = BeautifulSoup(html, 'html.parser').select_one('.c-cardapios')
    if page is None:
        raise ValueError(f'Página de cardápio ausente em {day}')

    date_header = page.select_one('table thead th:nth-child(2)')
    if date_header is None or f'({day:%d/%m})' not in date_header.get_text():
        raise ValueError(f'Data do cardápio não corresponde a {day}')

    if 'Não há cardápio cadastrado para este dia' in page.get_text(' ', strip=True):
        return None

    menu = []
    for period in ('desjejum', 'almoco', 'jantar'):
        table = page.select_one(f'table.refeicao.{period}')
        items = []
        if table is not None:
            for row in table.select('tr.item'):
                category, dishes = row.find_all('td', recursive=False)
                for line_break in dishes.find_all('br'):
                    line_break.replace_with('\n')
                for line in dishes.get_text().splitlines():
                    item = ' '.join(line.split())
                    if item:
                        items.append(f'{category.get_text(strip=True)}: {item}')
            if not items:
                raise ValueError(f'Tabela de {period} vazia em {day}')
        menu.append(items or [NO_MEALS])

    if all(meal == [NO_MEALS] for meal in menu):
        raise ValueError(f'Nenhuma tabela de refeição encontrada em {day}')
    return {'weekday': WEEKDAYS[day.weekday()], 'menu': menu}


def upload(firebase, menus):
    city = firebase.call(CITY) or {}
    if city.get('university', 'UFC') != 'UFC':
        raise RuntimeError('A chave ufc-for já pertence a outra universidade')
    restaurant = (city.get('rus') or {}).get('ru-ufc') or {}
    stored = {f'{CITY}/{key}': value for key, value in city.items()}
    stored.update({f'{RESTAURANT}/{key}': value for key, value in restaurant.items()})

    changes = {path: value for path, value in METADATA.items() if path not in stored}
    timestamp = int(time.time())
    for day, payload in menus.items():
        changes[f'archive/{RESTAURANT}/menus/{day}'] = dict(payload, timestamp=timestamp)

    if changes:
        firebase.call('', changes)
        for path, expected in changes.items():
            if firebase.call(path) != expected:
                raise RuntimeError(f'Falha na verificação do Firebase em {path}')
    print(f'[UFC] Cadastro e {len(menus)} cardápio(s) publicados e verificados.')


def main():
    today = dt.datetime.now(ZoneInfo('America/Fortaleza')).date()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=dt.date.fromisoformat, default=today)
    parser.add_argument('--end', type=dt.date.fromisoformat)
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    end = args.end or args.start + dt.timedelta(days=6)
    if end < args.start:
        parser.error('--end deve ser igual ou posterior a --start')

    menus = {}
    with requests.Session() as session:
        for offset in range((end - args.start).days + 1):
            day = args.start + dt.timedelta(days=offset)
            response = session.get(f'{SOURCE}/{day}', timeout=20)
            response.raise_for_status()
            payload = parse_day(response.content, day)
            if payload:
                menus[day.isoformat()] = payload

    if args.upload:
        upload(Firebase(os.getenv('BASE_URL'), os.getenv('FIREBASE_KEY')), menus)
    else:
        print(json.dumps(menus, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
