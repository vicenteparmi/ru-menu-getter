#!/usr/bin/env python3
"""Collect UFV's public calendar JSON and publish CampusDine menus, without AI."""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

PORTAL = 'http://cardapio.ufv.br/'
CITY = 'ufv-vicosa'
NO_MEALS = 'Sem refeições disponíveis'
WEEKDAYS = ['Segunda-Feira', 'Terça-Feira', 'Quarta-Feira', 'Quinta-Feira',
            'Sexta-Feira', 'Sábado', 'Domingo']
RESTAURANTS = {
    'ru-i': 'Restaurante Universitário I (RU I)',
    'ru-ii': 'Restaurante Universitário II (RU II)',
    'ru-iii': 'Restaurante Universitário III (Multiuso)',
}
# Labels, rather than numerical group IDs, identify which physical units serve a meal.
REFECTORIES = {
    'RU I': ('ru-i',),
    'RU II': ('ru-ii',),
    'RU III': ('ru-iii',),
    'RU III (Multiuso)': ('ru-iii',),
    'RU - II e RU III': ('ru-ii', 'ru-iii'),
}
MEALS = {'3': 0, '4': 1, '5': 2}


def clean(value):
    if not isinstance(value, str):
        raise ValueError('Expected a text field from UFV')
    return ' '.join(html.unescape(value).split())


def request(url, *, data=None, method=None):
    """Bounded retries; never include credential-bearing URLs in errors."""
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={'User-Agent': 'CampusDine UFV collector/1.0'})
        if data is not None:
            req.add_header('Content-Type', 'application/json' if method == 'PATCH'
                           else 'application/x-www-form-urlencoded')
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f'HTTP request failed (status {error.code})') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise RuntimeError('HTTP request failed after three attempts') from None
        time.sleep(attempt + 1)


def discover_endpoint():
    page = request(PORTAL).decode('utf-8')
    match = re.search(r'url:\s*[\'"]([^\'"]*ajaxBuscaCardapioPorData\.php)[\'"]', page)
    if not match:
        raise ValueError('UFV calendar endpoint not found')
    endpoint = urllib.parse.urljoin(PORTAL, match.group(1))
    if urllib.parse.urlsplit(endpoint).netloc != 'cardapio.ufv.br':
        raise ValueError('Unexpected UFV calendar host')
    return endpoint


def parse_day(payload, date):
    if not isinstance(payload, dict) or type(payload.get('retorno')) is not bool:
        raise ValueError('Unexpected UFV response')
    rows = payload.get('dados')
    if not isinstance(rows, list):
        raise ValueError('UFV response has no data list')
    if not payload['retorno']:
        if rows:
            raise ValueError('UFV response reports failure with data')
        return {}
    if not rows:
        raise ValueError('UFV reports success without any items')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('data') != date.isoformat():
            raise ValueError(f'Unexpected UFV item date for {date}')
        restaurants = REFECTORIES.get(clean(row.get('Refeitorio')))
        meal = MEALS.get(str(row.get('refeicao_id')))
        if not restaurants or meal is None:
            raise ValueError(f'Unknown UFV refectory or meal on {date}')
        item = clean(row.get('composicao'))
        if not item:
            raise ValueError(f'Empty UFV item on {date}')
        category = clean(row.get('categoria'))
        if category and category != '.':
            item = f'{category.capitalize()}: {item}'
        note = clean(row.get('obs_composicao') or '')
        if note:
            item += f' ({note})'
        for restaurant in restaurants:
            meals = result.setdefault(restaurant, [[], [], []])
            if item not in meals[meal]:
                meals[meal].append(item)
            note = clean(row.get('obs_cardapio') or '')
            if note and f'Observação: {note}' not in meals[meal]:
                meals[meal].append(f'Observação: {note}')
    return result


def collect(start, days):
    endpoint = discover_endpoint()
    published = {}
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        body = urllib.parse.urlencode({'data_selecionada': date.strftime('%d/%m/%Y')}).encode()
        menus = parse_day(json.loads(request(endpoint, data=body)), date)
        if menus:
            published[date] = menus
    if not published:
        raise ValueError('No UFV menus published in the requested range; nothing written')
    return build_menus(published)


def build_menus(published):
    active = sorted({restaurant for menus in published.values() for restaurant in menus})
    result = {restaurant: {} for restaurant in active}
    for date, menus in published.items():
        for restaurant in active:
            meals = menus.get(restaurant, [[], [], []])
            result[restaurant][date.isoformat()] = {
                'weekday': WEEKDAYS[date.weekday()],
                'menu': [items if items else [NO_MEALS] for items in meals],
                'timestamp': 0,
            }
    return result


class Firebase:
    def __init__(self, base_url, auth):
        parsed = urllib.parse.urlsplit(base_url or '')
        if parsed.scheme != 'https' or not parsed.netloc or parsed.query or not auth:
            raise ValueError('Configure HTTPS BASE_URL and FIREBASE_KEY for upload')
        self.base = base_url.rstrip('/')
        self.auth = auth

    def call(self, path, data=None):
        url = f'{self.base}/{path}.json?{urllib.parse.urlencode({"auth": self.auth})}'
        body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
        return json.loads(request(url, data=body, method='PATCH' if body else 'GET'))

    def upload(self, menus):
        existing = self.call(f'menus/{CITY}') or {}
        if existing.get('university', 'UFV') != 'UFV':
            raise ValueError('UFV location key belongs to a different university')
        changes = {}
        # Add missing metadata only: preserve settings maintained by the app's admins.
        for field, value in {'name': 'Viçosa, Minas Gerais', 'university': 'UFV'}.items():
            if field not in existing:
                changes[f'menus/{CITY}/{field}'] = value
        timestamp = int(time.time())
        expected = {}
        for restaurant, dates in menus.items():
            metadata = {
                'name': RESTAURANTS[restaurant], 'address': 'Campus UFV - Viçosa, MG',
                'displayMessage': False, 'isNew': True, 'status': 'beta',
                'updateFrequency': 'daily', 'updateModeIsAuto': True,
            }
            stored = (existing.get('rus') or {}).get(restaurant) or {}
            for field, value in metadata.items():
                if field not in stored:
                    changes[f'menus/{CITY}/rus/{restaurant}/{field}'] = value
            for date, payload in dates.items():
                path = f'archive/menus/{CITY}/rus/{restaurant}/menus/{date}'
                expected[path] = dict(payload, timestamp=timestamp)
                changes[path] = expected[path]
        # One atomic multi-location PATCH; other universities and dates stay untouched.
        self.call('', changes)
        for path, payload in expected.items():
            if self.call(path) != payload:
                raise RuntimeError(f'Firebase verification failed for {path}')
        catalog = self.call(f'menus/{CITY}')
        for restaurant in menus:
            if not catalog.get('rus', {}).get(restaurant, {}).get('name'):
                raise RuntimeError('Firebase catalog verification failed')
        print(f'[UFV] {len(expected)} restaurant-days uploaded and read back successfully.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=dt.date.fromisoformat,
                        default=dt.datetime.now(ZoneInfo('America/Sao_Paulo')).date())
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--upload', action='store_true', help='Write and verify Firebase data')
    parser.add_argument('--output', help='Save collected menus as JSON')
    args = parser.parse_args()
    if not 1 <= args.days <= 31:
        parser.error('--days must be between 1 and 31')
    try:
        menus = collect(args.start, args.days)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as file:
                json.dump({CITY: menus}, file, ensure_ascii=False, indent=2)
        print(json.dumps({CITY: {key: sorted(dates) for key, dates in menus.items()}}, indent=2))
        if args.upload:
            Firebase(os.environ.get('BASE_URL'), os.environ.get('FIREBASE_KEY')).upload(menus)
        return 0
    except (ValueError, RuntimeError) as error:
        print(f'[UFV ERROR] {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
