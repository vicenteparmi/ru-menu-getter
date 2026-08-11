#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

from main import process_pdf_menu


class ProcessPdfMenuTests(unittest.TestCase):
    @patch("main.process_pdf_inline")
    def test_returns_validated_menu(self, process_pdf_inline):
        process_pdf_inline.return_value = json.dumps({
            "2026-08-10": {
                "menu": [["Sem refeições disponíveis"], ["Arroz"], ["Sopa"]],
                "timestamp": 0,
                "weekday": "Segunda-Feira",
            }
        })

        result = process_pdf_menu("menu.pdf")

        self.assertEqual(list(result), ["2026-08-10"])
        self.assertEqual(len(result["2026-08-10"]["menu"]), 3)

    @patch("main.process_pdf_inline")
    def test_rejects_entire_response_when_any_day_is_invalid(self, process_pdf_inline):
        process_pdf_inline.return_value = json.dumps({
            "2026-08-10": {
                "menu": [["Sem refeições disponíveis"], ["Arroz"], ["Sopa"]],
                "timestamp": 0,
                "weekday": "Segunda-Feira",
            },
            "2026-08-11": {
                "menu": [["Sem refeições disponíveis"], ["Arroz"]],
                "timestamp": 0,
                "weekday": "Terça-Feira",
            },
        })

        self.assertIsNone(process_pdf_menu("menu.pdf"))


if __name__ == "__main__":
    unittest.main()
