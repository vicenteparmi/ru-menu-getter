import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import UFV


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.date = dt.date(2026, 10, 29)
        self.payload = json.loads((Path(__file__).parent / 'fixtures/ufv-2026-10-29.json').read_text())

    def test_real_menu_distributes_shared_lunch_only(self):
        parsed = UFV.parse_day(self.payload, self.date)
        self.assertEqual(set(parsed), {'ru-ii', 'ru-iii'})
        self.assertEqual(parsed['ru-ii'][1], parsed['ru-iii'][1])
        self.assertIn('Prato principal: Frango Cremoso', parsed['ru-ii'][1])
        self.assertIn('Opção vegana: Ervilha ao Molho Napolitano', parsed['ru-iii'][1])
        self.assertEqual(parsed['ru-ii'][0], [])
        self.assertEqual(parsed['ru-ii'][2], [])
        self.assertTrue(any('Lactose' in item for item in parsed['ru-iii'][0]))
        menus = UFV.build_menus({self.date: parsed})
        self.assertEqual(menus['ru-ii']['2026-10-29']['menu'][0], [UFV.NO_MEALS])
        self.assertEqual(menus['ru-iii']['2026-10-29']['weekday'], 'Quinta-Feira')

    def test_bad_source_aborts_instead_of_guessing(self):
        for field, value in [('data', '2025-10-29'), ('Refeitorio', 'RU desconhecido'),
                             ('refeicao_id', '99'), ('composicao', ''), ('categoria', None)]:
            with self.subTest(field=field):
                payload = copy.deepcopy(self.payload)
                payload['dados'][0][field] = value
                with self.assertRaises(ValueError):
                    UFV.parse_day(payload, self.date)

    def test_missing_date_is_skipped_and_inconsistent_response_rejected(self):
        self.assertEqual(UFV.parse_day({'retorno': False, 'dados': []}, self.date), {})
        for payload in [{'retorno': True, 'dados': []}, {'retorno': False, 'dados': [{}]}, {}]:
            with self.assertRaises(ValueError):
                UFV.parse_day(payload, self.date)

    def test_optional_notes_can_be_null(self):
        expected = UFV.parse_day(self.payload, self.date)
        for row in self.payload['dados']:
            row['obs_composicao'] = None
            row['obs_cardapio'] = None
        self.assertEqual(UFV.parse_day(self.payload, self.date), expected)

    def test_unit_not_serving_on_published_day_gets_no_meals(self):
        parsed = UFV.parse_day(self.payload, self.date)
        tomorrow = self.date + dt.timedelta(days=1)
        menus = UFV.build_menus({self.date: parsed, tomorrow: {'ru-iii': parsed['ru-iii']}})
        self.assertEqual(menus['ru-ii'][tomorrow.isoformat()]['menu'], [[UFV.NO_MEALS]] * 3)


class FirebaseTests(unittest.TestCase):
    def setUp(self):
        self.date = dt.date(2026, 10, 29)
        self.menus = UFV.build_menus({self.date: {'ru-iii': [['Pão'], ['Arroz'], []]}})

    def test_atomic_scoped_patch_preserves_admin_settings_and_other_data(self):
        existing = {'name': 'Viçosa, Minas Gerais', 'university': 'UFV',
                    'rus': {'ru-i': {'name': 'RU I'}, 'ru-iii': {'name': 'Custom name', 'status': 'maintenance', 'isNew': False}}}
        writes = []
        def fake_call(path, data=None):
            if data is not None:
                writes.append((path, data))
                return data
            if path == f'menus/{UFV.CITY}':
                return existing
            return writes[0][1][path]
        store = UFV.Firebase('https://example.firebaseio.com', 'test-auth')
        with patch.object(store, 'call', side_effect=fake_call):
            store.upload(self.menus)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][0], '')
        changes = writes[0][1]
        self.assertNotIn(f'menus/{UFV.CITY}/rus/ru-iii/status', changes)
        self.assertNotIn(f'menus/{UFV.CITY}/rus/ru-iii/isNew', changes)
        self.assertTrue(all(path.startswith((f'menus/{UFV.CITY}/', f'archive/menus/{UFV.CITY}/')) for path in changes))
        self.assertEqual(changes[f'archive/menus/{UFV.CITY}/rus/ru-iii/menus/2026-10-29']['menu'][2], [UFV.NO_MEALS])

    def test_closed_ru_i_is_catalog_only_and_admin_notice_is_preserved(self):
        existing = {'university': 'UFV', 'rus': {
            'ru-i': {'name': 'Restaurante Universitário I (RU I)', 'messageContent': 'Aviso revisado'},
            'ru-iii': {'name': 'Multiuso'},
        }}
        writes = []
        def fake_call(path, data=None):
            if data is not None:
                writes.append(data)
                return data
            if path == f'menus/{UFV.CITY}':
                return existing
            return writes[0][path]
        store = UFV.Firebase('https://example.firebaseio.com', 'test-auth')
        with patch.object(store, 'call', side_effect=fake_call):
            store.upload(self.menus)
        changes = writes[0]
        prefix = f'menus/{UFV.CITY}/rus/ru-i/'
        self.assertEqual(changes[prefix + 'name'], 'RU I')
        self.assertNotIn(f'menus/{UFV.CITY}/rus/ru-iii/name', changes)
        self.assertEqual(changes[prefix + 'status'], 'maintenance')
        self.assertTrue(changes[prefix + 'displayMessage'])
        self.assertEqual(changes[prefix + 'messageTitle'], 'Fechado para reforma')
        self.assertNotIn(prefix + 'messageContent', changes)
        self.assertFalse(any(path.startswith(f'archive/menus/{UFV.CITY}/rus/ru-i/')
                             for path in changes))

    def test_failed_readback_is_reported(self):
        store = UFV.Firebase('https://example.firebaseio.com', 'test-auth')
        with patch.object(store, 'call', side_effect=[None, {}, {'bad': 'data'}]):
            with self.assertRaises(RuntimeError):
                store.upload(self.menus)

    def test_firebase_requires_https_and_credentials(self):
        for url, auth in [('http://example.com', 'key'), ('https://example.com', ''), ('', 'key')]:
            with self.assertRaises(ValueError):
                UFV.Firebase(url, auth)


if __name__ == '__main__':
    unittest.main()
