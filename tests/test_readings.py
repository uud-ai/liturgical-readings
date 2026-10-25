"""Проверки по контрольным датам.

Эталон для воскресений октября 2026 г. — azbyka.ru/biblia/days (сверено
25.10.2026). Запуск: python -m unittest discover tests
"""

import unittest
from datetime import date

from src.cycle import computed_pascha, eothinon, resolve
from src.links import bible_url
from src.readings import get_reading


class PaschaTest(unittest.TestCase):
    def test_known_dates(self):
        known = {
            2020: date(2020, 4, 19), 2021: date(2021, 5, 2),
            2022: date(2022, 4, 24), 2023: date(2023, 4, 16),
            2024: date(2024, 5, 5), 2025: date(2025, 4, 20),
            2026: date(2026, 4, 12), 2027: date(2027, 5, 2),
            2028: date(2028, 4, 16), 2029: date(2029, 4, 8),
            2030: date(2030, 4, 28),
        }
        for year, expected in known.items():
            self.assertEqual(computed_pascha(year), expected, year)


class CycleTest(unittest.TestCase):
    def pos(self, y, m, d):
        return resolve(date(y, m, d))

    def test_pascha_period(self):
        p = self.pos(2026, 4, 19)  # Антипасха
        self.assertEqual((p.apostle.week, p.apostle.weekday), ("2", "sun"))
        p = self.pos(2026, 4, 13)  # понедельник Светлой седмицы
        self.assertEqual((p.apostle.week, p.apostle.weekday), ("2", "mon"))
        self.assertEqual(self.pos(2026, 5, 31).apostle.week, "pentecost")

    def test_lukan_jump_2026(self):
        # Воздвижение 27.09.2026 — воскресенье, Неделя по Воздвижении 04.10.
        # 18.10: Апостол 20-й Недели, Евангелие 19-й (отступка).
        p = self.pos(2026, 10, 18)
        self.assertEqual((p.apostle.week, p.gospel.week), ("20", "19"))
        # До Недели по Воздвижении включительно — без сдвига.
        p = self.pos(2026, 10, 4)
        self.assertEqual((p.apostle.week, p.gospel.week), ("18", "18"))
        # Понедельник после неё — Лк 3:19-22, рядовое 18-й седмицы.
        p = self.pos(2026, 10, 5)
        self.assertEqual((p.apostle.week, p.gospel.week), ("19", "18"))

    def test_triodion_bounds(self):
        # Неделя о мытаре и фарисее 2027 — 21.02.2027, Великая Суббота — 01.05.2027.
        self.assertEqual(self.pos(2027, 2, 21).triodion_day, 70)
        self.assertEqual(self.pos(2027, 5, 1).triodion_day, 1)
        self.assertIsNone(self.pos(2027, 2, 20).triodion_day)
        self.assertIsNone(self.pos(2027, 5, 2).triodion_day)

    def test_winter_period_not_implemented(self):
        # Неделя святых отец 03.01.2027 … суббота перед Закхеем 13.02.2027.
        self.assertFalse(self.pos(2027, 1, 2).unresolved)
        self.assertTrue(self.pos(2027, 1, 3).unresolved)
        self.assertTrue(self.pos(2027, 2, 13).unresolved)

    def test_zacchaeus(self):
        p = self.pos(2027, 2, 14)
        self.assertEqual((p.apostle.week, p.gospel.week, p.apostle.weekday),
                         ("32", "32", "sun"))
        p = self.pos(2027, 2, 15)
        self.assertEqual((p.apostle.week, p.gospel.week, p.apostle.weekday),
                         ("33", "33", "mon"))

    def test_eothinon(self):
        self.assertEqual(eothinon(1)[1], "Мф.28:16-20")
        self.assertEqual(eothinon(20)[1], "Ин.20:19-31")  # 18.10.2026
        self.assertEqual(eothinon(21)[1], "Ин.21:1-14")   # 25.10.2026
        self.assertEqual(eothinon(12)[0], 1)


class ReadingTest(unittest.TestCase):
    def test_2026_10_25(self):
        text = get_reading(date(2026, 10, 25)).format()
        self.assertIn("Апостол: Гал.2:16-20 (зач. 203)", text)
        self.assertIn("Евангелие: Лк.7:11-16 (зач. 30)", text)
        self.assertIn("Ин.21:1-14 (зач. 66)", text)

    def test_myrrhbearers(self):
        text = get_reading(date(2026, 4, 26)).format()
        self.assertIn("Евангелие: Мк.15:43-16:8 (зач. 69)", text)
        self.assertIn("Евангелие утреннее: Мк.16:9-20 (зач. 71)", text)

    def test_triodion_2026(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2026, 2, 1)).format()   # Неделя о мытаре и фарисее
        self.assertIn("Евангелие 1-е воскресное: Мф.28:16-20 (зач. 116)", t)
        self.assertIn("Лк.18:10-14 (зач. 89)", t)
        t = get_reading(date(2026, 2, 14)).format()  # Вселенская родительская суббота
        self.assertIn("Апостол за упокой: 1Фес.4:13-17 (зач. 270)", t)
        t = get_reading(date(2026, 3, 8)).format()   # Неделя 2-я поста
        self.assertIn("Евангелие 6-е воскресное: Лк.24:36-53 (зач. 114)", t)
        self.assertIn("Евангелие святителю: Ин.10:9-16 (зач. 36)", t)
        t = get_reading(date(2026, 3, 17)).format()  # вторник 4-й седмицы
        self.assertIn("6-й час. Паремия: Ис.25:1-9", t)
        self.assertIn("Притч.12:8-22", t)
        t = get_reading(date(2026, 4, 9)).format()   # Великий Четверг
        self.assertIn("Мф.26:1-20 (зач. 107); Ин.13:3-17 (зач. 44)", t)
        t = get_reading(date(2026, 4, 10)).format()  # Великая Пятница
        self.assertIn("Евангелие Страстей 12-е: Мф.27:62-66 (зач. 114)", t)
        self.assertIn("Мф.27:55-61", t)

    def test_bible_links(self):
        # Коды книг — как на страницах azbyka.ru/biblia.
        self.assertEqual(bible_url("Иак.2:14-26"), "https://azbyka.ru/biblia/?Jac.2:14-26")
        self.assertEqual(bible_url("Евр.7:26-8:2"), "https://azbyka.ru/biblia/?Hebr.7:26-8:2")
        self.assertEqual(bible_url("Флп.1:1-7"), "https://azbyka.ru/biblia/?Phil.1:1-7")
        self.assertEqual(bible_url("3Цар.17:8-24"), "https://azbyka.ru/biblia/?1King.17:8-24")

    def test_triodion_table_complete(self):
        from src.readings import load_triodion
        t = load_triodion()
        for n in range(1, 71):
            self.assertTrue(t[str(n)]["readings"], n)
            for r in t[str(n)]["readings"]:
                for ref in [r.get("ref")] + [p["ref"] for p in r.get("parts", [])]:
                    if ref:
                        self.assertIsNotNone(bible_url(ref), ref)

    def test_full_ordinary_cycle(self):
        # В реализованных периодах нет дней без данных.
        d = date(2026, 1, 1)
        while d < date(2036, 1, 1):
            self.assertNotIn("ещё не внесено", get_reading(d).format(), d)
            d = date.fromordinal(d.toordinal() + 1)

    def test_every_day_formats(self):
        d = date(2026, 1, 1)
        while d < date(2031, 1, 1):
            get_reading(d).format()
            d = date.fromordinal(d.toordinal() + 1)


if __name__ == "__main__":
    unittest.main()
