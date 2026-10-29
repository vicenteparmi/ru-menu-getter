#!/usr/bin/env python3
"""Read the CCA/Joinville PDF on the existing server, without AI or OCR."""
import argparse
import datetime
import json
from pathlib import Path
from scrapers import FlorianopolisCCAScraper, JoinvilleScraper


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('restaurant', choices=['cca', 'joinville'])
    parser.add_argument('--date', type=datetime.date.fromisoformat, default=datetime.date.today())
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    scraper = {'cca': FlorianopolisCCAScraper, 'joinville': JoinvilleScraper}[args.restaurant]()
    menu = scraper.get_menu_data(args.date)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as file:
        json.dump(menu, file, ensure_ascii=False, indent=2)
    print(f'{args.restaurant}: {len(menu)} dias extraídos sem IA; salvos em {args.output}')


if __name__ == '__main__':
    main()
