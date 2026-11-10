import os
import unittest
from unittest.mock import Mock, patch
from utfpr_firebase_uploader import upload_utfpr_menu_to_firebase


class UploadTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, BASE_URL='https://example.com', FIREBASE_KEY='test')
        env.start()
        self.addCleanup(env.stop)
        delay = patch('utfpr_firebase_uploader.time.sleep')
        delay.start()
        self.addCleanup(delay.stop)
        self.menu = {day: {'menu': [['Sem refeições disponíveis'], ['Arroz'], ['Sopa']],
                           'weekday': 'Segunda-Feira', 'timestamp': 123}
                     for day in ('2026-11-09', '2026-11-10')}

    @patch('utfpr_firebase_uploader.requests.get')
    @patch('utfpr_firebase_uploader.requests.put')
    def test_partial_write_is_failure(self, put, get):
        put.side_effect = [Mock(status_code=200), Mock(status_code=500, text='error')]
        get.return_value.json.return_value = self.menu['2026-11-09']
        self.assertFalse(upload_utfpr_menu_to_firebase(self.menu))

    @patch('utfpr_firebase_uploader.requests.get')
    @patch('utfpr_firebase_uploader.requests.put')
    def test_readback_mismatch_is_failure(self, put, get):
        put.return_value.status_code = 200
        get.return_value.json.return_value = {'menu': []}
        self.assertFalse(upload_utfpr_menu_to_firebase(self.menu))

    @patch('utfpr_firebase_uploader.requests.get')
    @patch('utfpr_firebase_uploader.requests.put')
    def test_all_writes_are_verified(self, put, get):
        put.return_value.status_code = 200
        get.return_value.json.side_effect = list(self.menu.values())
        self.assertTrue(upload_utfpr_menu_to_firebase(self.menu))
        self.assertEqual(get.call_count, 2)
