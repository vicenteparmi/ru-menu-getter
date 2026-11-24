"""Collect one UFSC menu and optionally publish its validated week."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

from scrapers import (BlumenauScraper, CuritibanosScraper, FlorianopolisCCAScraper,
                      FlorianopolisTrindadeScraper, JoinvilleScraper)
from scrapers.pdf_menu import NO_MEALS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from UFV import Firebase

CAMPUSES = {
    'blumenau': ('ufsc-blu', BlumenauScraper),
    'curitibanos': ('ufsc-cur', CuritibanosScraper),
    'cca': ('ufsc-flo', FlorianopolisCCAScraper),
    'trindade': ('ufsc-flo', FlorianopolisTrindadeScraper),
    'joinville': ('ufsc-joi', JoinvilleScraper),
}


def validated_week(menus, date):
    monday = date - dt.timedelta(days=date.weekday())
    result = {}
    for key, day in sorted(menus.items()):
        offset = (dt.date.fromisoformat(key) - monday).days
        if not 0 <= offset < 7:
            continue
        meals = day['menu']
        if len(meals) != 3 or any(not meal or not all(isinstance(item, str) and item.strip() for item in meal)
                                  for meal in meals):
            raise ValueError(f'Slots de refeições inválidos para {key}')
        if any(meal != [NO_MEALS] for meal in meals):
            result[key] = day
    if not result or (date.weekday() < 5 and date.isoformat() not in menus):
        raise ValueError(f'Cardápio da semana de {date} ausente ou vazio')
    return result


def publish(campus, city, menus):
    firebase = Firebase(os.environ.get('BASE_URL'), os.environ.get('FIREBASE_KEY'))
    if not firebase.call(f'menus/{city}/rus/{campus}'):
        raise ValueError(f'Unidade ausente no catálogo: {city}/{campus}')
    prefix = f'archive/menus/{city}/rus/{campus}/menus'
    stamp = int(time.time())
    expected = {date: dict(day, timestamp=stamp) for date, day in menus.items()}
    firebase.call(prefix, {f'{date}/{key}': value for date, day in expected.items()
                           for key, value in day.items()})
    for date, day in expected.items():
        stored = firebase.call(f'{prefix}/{date}') or {}
        if any(stored.get(key) != value for key, value in day.items()):
            raise RuntimeError(f'Divergência ao reler {city}/{campus}/{date}')
        print(f'{city}/{campus}/{date}: gravado e verificado')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campus', choices=CAMPUSES)
    parser.add_argument('--date', type=dt.date.fromisoformat,
                        default=dt.datetime.now(ZoneInfo('America/Sao_Paulo')).date())
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    city, scraper = CAMPUSES[args.campus]
    reference = args.date
    if args.campus == 'cca' and reference.weekday() >= 5:
        reference -= dt.timedelta(days=reference.weekday() - 4)
    menus = validated_week(scraper().get_menu_data(reference), args.date)
    if args.upload:
        publish(args.campus, city, menus)
    else:
        print(json.dumps(menus, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
