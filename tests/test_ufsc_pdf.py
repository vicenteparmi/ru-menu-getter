import copy
import datetime as dt
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'RU-AI-GETTER'))
from scrapers.pdf_menu import cca_table, joinville_table, dates_in_text, NO_MEALS
from scrapers.base_scraper import RestaurantScraper

FIXTURES = Path(__file__).parent / 'fixtures'

class PdfMenuTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((FIXTURES / f'ufsc-{name}-2026-10-26.json').read_text())

    def test_cca_real_table_and_explicit_holiday(self):
        fixture = self.fixture('cca')
        result = cca_table(fixture['table'], fixture['text'])
        self.assertEqual(len(result), 5)
        self.assertEqual(result['2026-10-28']['menu'], [[NO_MEALS]]*3)
        meal = result['2026-10-29']['menu']
        self.assertIn('Farofa de cebola', meal[1])
        self.assertEqual(meal[1], meal[2])
        self.assertEqual(meal[0], [NO_MEALS])

    def test_joinville_real_table_preserves_weekend_breakfast_closure(self):
        result = joinville_table(self.fixture('joinville')['table'])
        self.assertEqual(len(result), 7)
        for date in ['2026-10-31', '2026-11-01']:
            self.assertEqual(result[date]['menu'][0], [NO_MEALS])
            self.assertTrue(result[date]['menu'][1])
        self.assertIn('Pão tipo francês c/ geléia', result['2026-10-29']['menu'][0])
        self.assertIn('Exclusivo para alunos isentos de pagamento', result['2026-10-29']['menu'][0])

    def test_changed_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            cca_table([['unknown']], 'Cardápio de 26 à 30/10/2026')
        with self.assertRaises(ValueError):
            joinville_table([['unknown']])

    def test_misordered_dates_are_rejected(self):
        table = copy.deepcopy(self.fixture('joinville')['table'])
        table[2][1] = '27/10/2025'
        with self.assertRaises(ValueError):
            joinville_table(table)

    def test_explicit_year_and_cross_month_range(self):
        dates = dates_in_text('Cardápio de 28.09 a 02.10.2026')
        self.assertEqual(dates[0], dt.date(2026, 9, 28))
        self.assertEqual(dates[-1], dt.date(2026, 10, 2))
        self.assertEqual(dates_in_text('Cardápio de 26 a 30/10'), [])

    def test_current_pdf_uses_content_dates_instead_of_first_link(self):
        scraper = RestaurantScraper()
        with patch.object(scraper, 'fetch_html', return_value='<a href="old.pdf">old</a><a href="new.pdf">new</a>'), \
             patch.object(scraper, 'download_pdf', side_effect=[io.BytesIO(b'old'), io.BytesIO(b'new')]), \
             patch.object(scraper, 'extract_text_from_pdf', side_effect=['26/10/2025', '26/10/2026']):
            pdf, _ = scraper.current_pdf('https://example.com', dt.date(2026, 10, 26))
            self.assertEqual(pdf.getvalue(), b'new')

    def test_old_document_is_not_a_fallback(self):
        scraper = RestaurantScraper()
        with patch.object(scraper, 'fetch_html', return_value='<a href="old.pdf">old</a>'), \
             patch.object(scraper, 'download_pdf', return_value=io.BytesIO(b'old')), \
             patch.object(scraper, 'extract_text_from_pdf', return_value='26/10/2025'):
            with self.assertRaises(ValueError):
                scraper.current_pdf('https://example.com', dt.date(2026, 10, 26))

if __name__ == '__main__':
    unittest.main()
