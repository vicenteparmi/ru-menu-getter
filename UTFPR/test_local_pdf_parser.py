import json
from pathlib import Path
import unittest
from unittest.mock import patch

from local_pdf_parser import parse_meal, parse_pdf, UnsupportedLayout


class LocalPdfTests(unittest.TestCase):
    def test_actual_source_columns_preserve_multiline_dishes_and_vegan_options(self):
        columns = json.loads((Path(__file__).parent / 'fixtures/nov9-2026-columns.json').read_text())
        for day in columns:
            lunch = parse_meal(day['lunch'], 'almoco')
            self.assertEqual(len(lunch), 12)
            self.assertTrue(lunch[4].startswith('Opção vegana:'))
            if day['date'] != '14/11':
                self.assertEqual(len(parse_meal(day['dinner'], 'jantar')), 12)
        self.assertIn('LOMBO AO MOLHO DE TOMATE', parse_meal(columns[4]['lunch'], 'almoco'))
        self.assertIn('FRANGO ASSADO AO MOLHO LARANJA', parse_meal(columns[0]['dinner'], 'jantar'))
        self.assertIn('Salada II', columns[0]['lunch'])

    def test_unknown_or_partial_column_cannot_be_published(self):
        for text in ('ALMOÇO\nArroz\nSobremesa', 'Jantar\nCarne\nPrato Principal', ''):
            with self.assertRaises(UnsupportedLayout):
                parse_meal(text, 'almoco')

    @patch('main.process_pdf_inline')
    @patch('main.parse_pdf')
    def test_local_success_does_not_call_paid_api(self, local, gemini):
        from main import process_pdf_menu
        local.return_value = {'2026-11-09': {'menu': [['Café'], ['Arroz'], ['Sopa']]}}
        self.assertEqual(process_pdf_menu('source.pdf'), local.return_value)
        gemini.assert_not_called()
