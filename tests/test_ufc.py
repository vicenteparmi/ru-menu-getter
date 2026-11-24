import datetime as dt
import unittest

from UFC import NO_MEALS, parse_day


def page(content, date='24/11'):
    return f'''
    <div class="c-cardapios">
      <table><thead><tr><th></th><th>Terça ({date})</th><th></th></tr></thead></table>
      {content}
    </div>
    '''


class UfcParserTest(unittest.TestCase):
    day = dt.date(2026, 11, 24)

    def test_preserves_categories_and_allergen_association(self):
        html = page('''
          <table class="refeicao almoco">
            <tr class="item"><td>Principal</td>
              <td><span>Frango</span><br><span>Creme</span><span> (Contém Lactose)</span></td>
            </tr>
            <tr class="item"><td>Vegetariano</td><td>Soja</td></tr>
          </table>
        ''')
        self.assertEqual(parse_day(html, self.day)['menu'], [
            [NO_MEALS],
            ['Principal: Frango', 'Principal: Creme (Contém Lactose)', 'Vegetariano: Soja'],
            [NO_MEALS],
        ])

    def test_unpublished_day_returns_no_payload(self):
        self.assertIsNone(parse_day(page('Não há cardápio cadastrado para este dia.'), self.day))

    def test_unexpected_markup_and_wrong_date_raise(self):
        for html in (page(''), page('', date='25/11'), '<html></html>'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_day(html, self.day)
