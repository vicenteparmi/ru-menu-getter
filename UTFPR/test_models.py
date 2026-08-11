#!/usr/bin/env python3

import unittest

from models import validate_menu_data


def valid_day(**overrides):
    day = {
        "menu": [
            ["Sem refeições disponíveis"],
            ["Arroz", "Feijão"],
            ["Sopa"],
        ],
        "timestamp": 0,
        "weekday": "Segunda-Feira",
    }
    day.update(overrides)
    return day


class MenuValidationTests(unittest.TestCase):
    def test_accepts_expected_database_shape(self):
        valid, processed, errors = validate_menu_data({"2026-08-10": valid_day()})

        self.assertTrue(valid)
        self.assertEqual(errors, [])
        self.assertEqual(processed["2026-08-10"]["timestamp"], 0)
        self.assertEqual(len(processed["2026-08-10"]["menu"]), 3)

    def test_rejects_missing_meal_period(self):
        valid, processed, errors = validate_menu_data({
            "2026-08-10": valid_day(menu=[["Café"], ["Almoço"]])
        })

        self.assertFalse(valid)
        self.assertEqual(processed, {})
        self.assertTrue(errors)

    def test_rejects_extra_meal_period(self):
        valid, processed, errors = validate_menu_data({
            "2026-08-10": valid_day(menu=[["Café"], ["Almoço"], ["Jantar"], ["Ceia"]])
        })

        self.assertFalse(valid)
        self.assertEqual(processed, {})
        self.assertTrue(errors)

    def test_rejects_weekday_that_does_not_match_date(self):
        valid, processed, errors = validate_menu_data({
            "2026-08-10": valid_day(weekday="Terça-Feira")
        })

        self.assertFalse(valid)
        self.assertEqual(processed, {})
        self.assertIn("does not match", errors[0])

    def test_rejects_timestamp_other_than_zero(self):
        valid, processed, errors = validate_menu_data({
            "2026-08-10": valid_day(timestamp=123)
        })

        self.assertFalse(valid)
        self.assertEqual(processed, {})
        self.assertTrue(errors)

    def test_rejects_extra_fields(self):
        valid, processed, errors = validate_menu_data({
            "2026-08-10": valid_day(source="unexpected")
        })

        self.assertFalse(valid)
        self.assertEqual(processed, {})
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
