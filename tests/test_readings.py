"""Проверки по контрольным датам.

Эталон для воскресений октября 2026 г. — azbyka.ru/biblia/days (сверено
25.10.2026). Запуск: python -m unittest discover tests
"""

import unittest
from datetime import date

from src.bible_text import passage
from src.cycle import computed_pascha, eothinon, resolve
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
        # До Недели по Воздвижении включительно Лукины чтения не начинаются: в год
        # отступки повторяются Евангелия 11-й седмицы (azbyka.ru 28.09–04.10.2026,
        # 24.09–30.09.2018; при двух недостающих — 10-й и 11-й: 20.09, 28.09, 03.10.2010).
        cases = {(2026, 9, 28): ("18", "11", "mon"), (2026, 10, 4): ("18", "11", "sun"),
                 (2018, 9, 29): ("18", "11", "sat"),
                 (2010, 9, 20): ("18", "10", "mon"), (2010, 9, 28): ("19", "11", "tue"),
                 (2010, 10, 3): ("19", "11", "sun")}
        for (y, m, d), expected in cases.items():
            p = self.pos(y, m, d)
            self.assertEqual((p.apostle.week, p.gospel.week, p.gospel.weekday), expected)
        # Понедельник после неё — Лк 3:19-22, рядовое 18-й седмицы.
        p = self.pos(2026, 10, 5)
        self.assertEqual((p.apostle.week, p.gospel.week), ("19", "18"))

    def test_triodion_bounds(self):
        # Неделя о мытаре и фарисее 2027 — 21.02.2027, Великая Суббота — 01.05.2027.
        self.assertEqual(self.pos(2027, 2, 21).triodion_day, 70)
        self.assertEqual(self.pos(2027, 5, 1).triodion_day, 1)
        self.assertIsNone(self.pos(2027, 2, 20).triodion_day)
        self.assertIsNone(self.pos(2027, 5, 2).triodion_day)

    def test_winter_period(self):
        # До Богоявления — прямой счёт с Лукиной преступкой (azbyka.ru 09.01.2025, 12.01.2026).
        p = self.pos(2026, 1, 12)
        self.assertEqual((p.apostle.week, p.gospel.week), ("32", "33"))
        p = self.pos(2025, 1, 9)
        self.assertEqual((p.apostle.week, p.gospel.week), ("29", "32"))
        # После Богоявления — обратный счёт (azbyka.ru 22.01.2025, 20.01.2026).
        p = self.pos(2026, 1, 20)
        self.assertEqual((p.apostle.week, p.gospel.week), ("32", "32"))
        p = self.pos(2025, 1, 22)
        self.assertEqual((p.apostle.week, p.gospel.week), ("31", "31"))
        self.assertFalse(self.pos(2027, 2, 14).unresolved)

    def test_christmas_period(self):
        # Год с Воздвиженской отступкой: с субботы пред Рождеством Апостол — по
        # седмице Евангелия (azbyka.ru/days: 01.01, 03.01, 10.01.2011; 02.01, 04.01,
        # 05.01, 11.01–13.01, 15.01, 16.01.2016).
        cases = {
            (2010, 12, 27): ("32", "30"), (2011, 1, 1): ("30", "30"),
            (2011, 1, 3): ("31", "31"), (2011, 1, 10): ("32", "32"),
            (2015, 12, 31): ("31", "30"), (2016, 1, 2): ("30", "30"),
            (2016, 1, 4): ("31", "31"), (2016, 1, 13): ("32", "32"),
            (2016, 1, 16): ("32", "32"),
            # Ранняя Пасха: седмицы исчерпаны — читается 33-я (azbyka.ru 15–17.01.2018).
            (2018, 1, 15): ("33", "33"), (2018, 1, 17): ("33", "33"),
        }
        for (y, m, d), weeks in cases.items():
            p = self.pos(y, m, d)
            self.assertFalse(p.unresolved, (y, m, d))
            self.assertEqual((p.apostle.week, p.gospel.week), weeks, (y, m, d))
        # Недели святых отец, по Рождестве, пред Богоявлением — без рядовых.
        for y, m, d in ((2016, 1, 3), (2016, 1, 10), (2016, 1, 17), (2026, 1, 18)):
            self.assertTrue(self.pos(y, m, d).ordinary_omitted, (y, m, d))
        t = get_reading(date(2016, 1, 13)).format()
        self.assertIn("Мк.11:23-26", t)

    def test_theophany_gap_sundays(self):
        # Крещенская отступка: воскресенья между Неделей по Богоявлении и Закхеем
        # заполняются назад от Закхея (azbyka.ru/days, сверено 25.10.2026).
        cases = {
            (2024, 1, 28): "30", (2024, 2, 4): "31", (2024, 2, 11): "17",  # три воскресенья
            (2013, 1, 27): "30", (2013, 2, 10): "17",
            (2019, 1, 27): "30", (2019, 2, 3): "31",                       # два
            (2021, 1, 31): "30", (2016, 1, 31): "30",
            (2022, 1, 30): "31",                                           # одно
            (2025, 1, 26): "31",              # Неделя по Богоявлении, под зачало
        }
        for (y, m, d), week in cases.items():
            p = self.pos(y, m, d)
            self.assertFalse(p.unresolved, (y, m, d))
            self.assertEqual((p.apostle.week, p.gospel.week, p.gospel.weekday),
                             (week, week, "sun"), (y, m, d))
        # Если пропущенные воскресенья есть, в Неделю по Богоявлении рядовых нет.
        for y, m, d in ((2024, 1, 21), (2022, 1, 23)):
            p = self.pos(y, m, d)
            self.assertTrue(p.ordinary_omitted, (y, m, d))
            t = get_reading(date(y, m, d)).format()
            self.assertIn("Мф.4:12-17", t)
            self.assertNotIn("рядовое (под зачало)", t)
        t = get_reading(date(2024, 2, 18)).format()
        self.assertIn("Неделя 37-я по Пятидесятнице", t)     # как на azbyka.ru
        self.assertIn("Лк.19:1-10", t)

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

    def test_fixed_feasts(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2026, 9, 21)).format()  # Рождество Богородицы, будни
        self.assertIn("Рождество Пресвятой Богородицы", t)
        self.assertIn("Литургия. Апостол: Флп.2:5-11 (зач. 240)", t)
        self.assertNotIn("Недели", t)
        t = get_reading(date(2025, 9, 21)).format()  # то же в воскресенье
        self.assertIn("Утреня. Евангелие: Лк.1:39-49,56 (зач. 4)", t)
        self.assertIn("Гал.6:11-18 (зач. 215)", t)          # Неделя пред Воздвижением
        self.assertIn("Апостол рядовой (под зачало): 2Кор.4:6-15 (зач. 176)", t)
        self.assertIn("Евангелие Богородицы: Лк.10:38-42,11:27-28 (зач. 54)", t)
        self.assertNotIn("воскресное", t)
        t = get_reading(date(2026, 9, 27)).format()  # Воздвижение в воскресенье
        self.assertIn("Ин.19:6-11,13-20,25-28,30-35 (зач. 60)", t)
        self.assertNotIn("Недели", t)
        t = get_reading(date(2026, 2, 15)).format()  # Сретение в Неделю мясопустную
        self.assertIn("Апостол Недели: 1Кор.8:8-9:2 (зач. 140)", t)
        self.assertIn("Евангелие праздника: Лк.2:22-40 (зач. 7)", t)
        t = get_reading(date(2026, 4, 7)).format()   # Благовещение в Великий Вторник
        self.assertIn("Евангелие Благовещения: Лк.1:24-38 (зач. 3)", t)
        self.assertIn("Мф.24:36-26:2", t)
        self.assertNotIn("Мф.22:15-23:39", t)            # утреня — Благовещения

    def test_eves(self):
        t = get_reading(date(2026, 1, 16)).format()  # Царские часы в пятницу
        self.assertIn("9-й час. Апостол: Тит.2:11-14,3:4-7 (зач. 302)", t)
        t = get_reading(date(2026, 1, 18)).format()  # навечерие в воскресенье
        self.assertIn("Евангелие 10-е воскресное: Ин.21:1-14 (зач. 66)", t)
        self.assertIn("Апостол Недели пред Богоявлением: 2Тим.4:5-8 (зач. 298)", t)
        self.assertIn("Евангелие: Лк.3:1-18 (зач. 9)", t)
        t = get_reading(date(2025, 1, 18)).format()  # навечерие в субботу
        self.assertIn("1Тим.3:14-4:5 (зач. 284)", t)
        t = get_reading(date(2027, 1, 6)).format()   # навечерие Рождества в среду
        self.assertIn("1-й час. Евангелие: Мф.1:18-25 (зач. 2)", t)
        self.assertIn("Вечерня с Литургией свт. Василия Великого. Евангелие: Лк.2:1-20 (зач. 5)", t)

    def test_special_days(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2025, 12, 28)).format()  # Неделя праотец
        self.assertIn("Кол.3:4-11 (зач. 257)", t)
        self.assertIn("Лк.14:16-24 (зач. 76)", t)
        t = get_reading(date(2026, 1, 3)).format()    # суббота пред Рождеством
        self.assertIn("Гал.3:8-12 (зач. 205)", t)
        self.assertIn("Апостол рядовой (под зачало): Еф.5:1-8 (зач. 228)", t)
        self.assertIn("Евангелие рядовое (под зачало): Лк.16:10-15 (зач. 81)", t)
        t = get_reading(date(2026, 1, 4)).format()    # Неделя святых отец
        self.assertIn("Евангелие 8-е воскресное: Ин.20:11-18 (зач. 64)", t)
        self.assertIn("Мф.1:1-25 (зач. 1)", t)
        t = get_reading(date(2026, 1, 10)).format()   # суббота по Рождестве
        self.assertIn("1Тим.6:11-16 (зач. 288)", t)
        t = get_reading(date(2026, 1, 11)).format()   # Неделя по Рождестве
        self.assertIn("Гал.1:11-19 (зач. 200)", t)
        self.assertIn("Мф.2:13-23 (зач. 4)", t)
        t = get_reading(date(2026, 1, 14)).format()   # Обрезание
        self.assertIn("Кол.2:8-12 (зач. 254)", t)
        t = get_reading(date(2026, 1, 24)).format()   # суббота по Богоявлении
        self.assertIn("Еф.6:10-17 (зач. 233)", t)
        self.assertIn("Апостол рядовой (под зачало): 1Фес.5:14-23 (зач. 273)", t)
        t = get_reading(date(2026, 1, 25)).format()   # Неделя по Богоявлении = о Закхее
        self.assertIn("Еф.4:7-13 (зач. 224 от полу)", t)
        self.assertIn("Евангелие рядовое (под зачало): Лк.19:1-10 (зач. 94)", t)

    def test_great_feasts(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2026, 7, 7)).format()    # Рождество Предтечи, будни
        self.assertIn("Литургия. Евангелие: Лк.1:1-25,57-68,76,80 (зач. 1)", t)
        self.assertIn("Рядовые чтения в этот день не читаются.", t)
        t = get_reading(date(2026, 7, 12)).format()   # Петра и Павла в воскресенье
        self.assertIn("Евангелие 6-е воскресное: Лк.24:36-53 (зач. 114)", t)
        self.assertIn("Апостол Недели: Рим.12:6-14 (зач. 110)", t)
        self.assertIn("Евангелие праздника: Мф.16:13-19 (зач. 67)", t)
        self.assertNotIn("Ин.21:15-25", t)
        t = get_reading(date(2026, 9, 11)).format()   # Усекновение
        self.assertIn("Мк.6:14-30 (зач. 24)", t)
        t = get_reading(date(2026, 10, 14)).format()  # Покров
        self.assertIn("Евр.9:1-7 (зач. 320)", t)

    def test_commemorations(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2025, 12, 19)).format()  # свт. Николай зимний (бдение, будни)
        self.assertIn("Утреня. Евангелие: Ин.10:9-16 (зач. 36)", t)
        self.assertIn("Рядовые чтения в этот день не читаются.", t)
        t = get_reading(date(2026, 5, 22)).format()   # свт. Николай вешний (пасхальный период)
        self.assertIn("Ин.14:1-11 (зач. 47)", t)
        self.assertIn("Апостол святителю: Евр.13:17-21 (зач. 335)", t)
        t = get_reading(date(2025, 11, 4)).format()   # Казанская (бдение)
        self.assertNotIn("Апостол Богородицы", t)
        self.assertIn("Литургия. Апостол: Флп.2:5-11 (зач. 240)", t)
        t = get_reading(date(2026, 9, 8)).format()    # Владимирская (полиелей)
        self.assertIn("Гал.2:21-3:7 (зач. 204)", t)
        self.assertIn("Апостол Богородицы: Флп.2:5-11 (зач. 240)", t)
        t = get_reading(date(2025, 12, 10)).format()  # Знамение
        self.assertIn("Апостол Богородицы: Евр.9:1-7 (зач. 320)", t)
        t = get_reading(date(2026, 4, 17)).format()   # Живоносный Источник
        self.assertIn("Ин.2:12-22 (зач. 7)", t)
        self.assertIn("Евангелие Богородицы: Лк.10:38-42,11:27-28 (зач. 54)", t)
        for d in (date(2026, 7, 26), date(2026, 10, 25)):  # отцы IV и VII Соборов
            self.assertIn("Апостол отцам: Евр.13:7-16 (зач. 334)", get_reading(d).format())
        t = get_reading(date(2026, 6, 14)).format()   # Все святые Российские
        self.assertIn("Апостол святым: Евр.11:33-12:2 (зач. 330)", t)
        for d in (date(2026, 2, 8), date(2025, 2, 9)):   # новомученики
            self.assertIn("Апостол мученикам: Рим.8:28-39 (зач. 99)", get_reading(d).format())
        self.assertNotIn("мученикам", get_reading(date(2026, 2, 1)).format())

    def test_saints(self):
        # Эталон — azbyka.ru/biblia/days (сверено 25.10.2026).
        t = get_reading(date(2026, 10, 8)).format()   # прп. Сергий (бдение)
        self.assertIn("Литургия. Евангелие: Лк.6:17-23 (зач. 24)", t)
        self.assertIn("Рядовые чтения в этот день не читаются.", t)
        t = get_reading(date(2026, 7, 18)).format()   # обретение мощей прп. Сергия + прмц. Елисавета
        self.assertIn("Утреня. Евангелие: Мф.11:27-30 (зач. 43)", t)
        self.assertIn("Рим.12:1-3 (зач. 108)", t)
        self.assertIn("Евангелие преподобномученице: Мк.5:24-34 (зач. 21)", t)
        t = get_reading(date(2025, 11, 21)).format()  # Собор Архистратига Михаила
        self.assertIn("Евр.2:2-10 (зач. 305)", t)
        t = get_reading(date(2025, 8, 2)).format()    # прор. Илия
        self.assertIn("Апостол пророку: Иак.5:10-20 (зач. 57)", t)
        t = get_reading(date(2026, 2, 6)).format()    # блж. Ксения
        self.assertIn("Мк.14:3-9 (зач. 63)", t)
        self.assertIn("Апостол блаженной: Гал.5:22-6:2 (зач. 213)", t)
        t = get_reading(date(2025, 12, 17)).format()  # вмц. Варвара
        self.assertIn("Евангелие великомученице: Мк.5:24-34 (зач. 21)", t)
        t = get_reading(date(2025, 12, 7)).format()   # вмц. Екатерина в воскресенье
        self.assertIn("Лк.13:10-17 (зач. 71)", t)
        self.assertIn("Апостол великомученице: Еф.6:10-17 (зач. 233)", t)
        t = get_reading(date(2026, 1, 27)).format()   # равноап. Нина (если служба)
        self.assertIn("если совершается служба", t)
        t = get_reading(date(2026, 9, 22)).format()   # прав. Иоаким и Анна
        self.assertIn("Евангелие богоотцам: Лк.8:16-21 (зач. 36)", t)

    def test_hierarchs_20th_century(self):
        t = get_reading(date(2026, 10, 28)).format()  # свт. Афанасий (Сахаров)
        self.assertIn("Кол.3:17-4:1 (зач. 259)", t)
        self.assertIn("Апостол святителю: Еф.6:10-17 (зач. 233)", t)
        t = get_reading(date(2026, 6, 11)).format()   # свт. Лука Крымский
        self.assertIn("Рим.5:10-16", t)
        self.assertIn("Евангелие святителю: Мф.5:14-19 (зач. 11)", t)
        t = get_reading(date(2025, 12, 25)).format()  # свт. Спиридон
        self.assertIn("Апостол святителю: Евр.13:17-21 (зач. 335)", t)

    def test_exaltation_days(self):
        t = get_reading(date(2026, 9, 20)).format()   # Неделя пред Воздвижением
        self.assertIn("Гал.6:11-18 (зач. 215)", t)
        self.assertIn("Евангелие рядовое (под зачало): Мф.25:14-30 (зач. 105)", t)
        t = get_reading(date(2025, 9, 20)).format()   # суббота пред Воздвижением
        self.assertIn("1Кор.2:6-9 (зач. 126)", t)
        self.assertIn("Апостол рядовой (под зачало): 1Кор.4:17-5:5 (зач. 132)", t)
        t = get_reading(date(2026, 10, 3)).format()   # суббота по Воздвижении
        self.assertIn("Ин.8:21-30 (зач. 30)", t)
        self.assertNotIn("Лк.4:31-36", t)
        self.assertIn("Евангелие рядовое (под зачало): Мф.19:3-12 (зач. 78)", t)
        t = get_reading(date(2026, 10, 4)).format()   # Неделя по Воздвижении
        self.assertIn("Мк.8:34-9:1 (зач. 37)", t)
        self.assertIn("Апостол рядовой (под зачало): 2Кор.9:6-11 (зач. 188)", t)

    def test_transfer_of_displaced_readings(self):
        # Рядовые будня, занятого праздником, — накануне или на следующий день
        # (azbyka.ru: «за среду», «за понедельник» и т. п.).
        cases = {
            date(2026, 10, 13): ("Апостол за среду (под зачало): Флп.2:24-30",
                                 "Евангелие за среду (под зачало): Лк.5:33-39"),   # Покров
            date(2026, 9, 22): ("Апостол за понедельник (под зачало): Еф.1:22-2:3",
                                "Мк.10:46-52"),            # Рождество Богородицы в пн
            date(2026, 10, 7): ("Апостол за четверг (под зачало): Флп.1:20-27",),  # прп. Сергий
            date(2026, 10, 10): ("Евангелие за пятницу (под зачало): Лк.4:22-30",),  # ап. Иоанн
            date(2025, 12, 3): ("Евангелие за четверг (под зачало): Лк.18:31-34",),  # Введение
            date(2018, 1, 4): ("Апостол за пятницу (под зачало): Иак.2:1-13",),  # царские часы
            date(2018, 1, 17): ("Евангелие за четверг (под зачало): Мк.12:38-44",),
            date(2020, 1, 16): ("Евангелие за пятницу (под зачало): Мк.13:1-8",),
        }
        for day, expected in cases.items():
            t = get_reading(day).format()
            for e in expected:
                self.assertIn(e, t, day)
        # Не переносятся: Рождество, Обрезание, Богоявление, прп. Серафим (azbyka.ru).
        for day in (date(2026, 1, 5), date(2026, 1, 13), date(2026, 1, 20),
                    date(2016, 1, 13), date(2020, 1, 16)):
            t = get_reading(day).format()
            self.assertNotIn("за вторник", t, day)
            self.assertNotIn("за среду", t, day)
            self.assertNotIn("за понедельник", t, day)
            self.assertNotIn("за четверг", t, day)

    def test_more_saints(self):
        # Памяти чтимых святых, сверенные с azbyka.ru/days (дата сверки — в data/feasts.json).
        cases = {
            date(2026, 10, 23): ("Апостол преподобному: Гал.5:22-6:2", "Мф.11:27-30"),  # прп. Амвросий
            date(2025, 2, 7): ("Апостол святителю: 1Кор.12:7-11", "Ин.10:1-9"),    # свт. Григорий
            date(2024, 11, 8): ("Евангелие великомученику: Ин.15:17-16:2",
                                "Апостол трясения: Евр.12:6-13,25-27"),             # вмч. Димитрий
            date(2025, 5, 21): ("Евангелие апостолу: Ин.19:25-27,21:24-25",),       # ап. Иоанн
            date(2025, 9, 19): ("Апостол Архангелу: Евр.2:2-10",),                  # чудо в Хонех
            date(2026, 1, 20): ("Евангелие Предтечи: Ин.1:29-34",),                 # Собор Предтечи
        }
        for day, expected in cases.items():
            t = get_reading(day).format()
            for e in expected:
                self.assertIn(e, t, day)
        # Свт. Иоанн Златоуст (бдение): рядовые переносятся на вторник.
        t = get_reading(date(2025, 11, 26)).format()
        self.assertIn("Рядовые чтения в этот день не читаются.", t)
        self.assertIn("Евангелие за среду (под зачало): Лк.15:1-10",
                      get_reading(date(2025, 11, 25)).format())
        # Условная память: чтения с пометкой; цвет облачения не меняется.
        r = get_reading(date(2025, 8, 15))
        self.assertIn("читаются, если совершается служба", r.format())
        self.assertEqual(r.vestment.key, "gold")
        # Малая память в воскресенье не читается (Косма и Дамиан, 14.11.2027 — воскресенье).
        self.assertNotIn("бессребреникам", get_reading(date(2027, 11, 14)).format())

    def test_theotokos_icons(self):
        # Иконы Божией Матери (azbyka.ru/days, дата сверки — в data/feasts.json).
        for day in (date(2025, 2, 25), date(2024, 11, 22), date(2025, 7, 25), date(2025, 9, 1)):
            t = get_reading(day).format()
            self.assertIn("Евангелие Богородицы: Лк.10:38-42,11:27-28", t, day)
            self.assertIn("Лк.1:39-49,56", t, day)
        self.assertIn("Апостол Богородицы: Евр.9:1-7", get_reading(date(2025, 8, 5)).format())
        t = get_reading(date(2025, 8, 29)).format()       # 16/29 августа — Нерукотворный Образ
        self.assertIn("Евангелие Образу: Лк.9:51-56,10:22-24", t)
        self.assertNotIn("Феодоровской", t)

    def test_christmas_theophany_edges(self):
        # Сверено с azbyka.ru/days (26.10.2026).
        t = get_reading(date(2024, 1, 6)).format()        # навечерие Рождества в субботу
        self.assertIn("Гал.3:15-22", t)
        self.assertIn("Мф.13:31-36", t)
        self.assertNotIn("Гал.3:8-12", t)
        t = get_reading(date(2025, 1, 18)).format()       # навечерие Богоявления в субботу
        self.assertIn("Апостол рядовой (под зачало): Еф.5:1-8", t)
        self.assertIn("Евангелие рядовое (под зачало): Лк.18:2-8", t)
        t = get_reading(date(2025, 1, 14)).format()       # Обрезание во вторник
        self.assertIn("Апостол Недели пред Богоявлением: 2Тим.4:5-8", t)
        self.assertNotIn("Недели пред Богоявлением", get_reading(date(2026, 1, 14)).format())
        self.assertTrue(get_reading(date(2025, 5, 29)).format().splitlines()[1]
                        .startswith("Вознесение Господне"))
        self.assertIn("Апостол блаженной: Гал.3:23-29",          # обретение мощей блж. Матроны
                      get_reading(date(2025, 3, 8)).format())

    def test_menaion(self):
        # Минея из Ponomar, сверено с azbyka.ru/days (26.10.2026).
        cases = {
            date(2026, 2, 10): ("(прп. Ефрема Сирина): Гал.5:22-6:2",),
            date(2025, 11, 15): ("Еф.6:10-17", "Мф.10:16-22"),          # мчч. Акиндин и др.
            date(2025, 6, 23): ("Евр.13:17-21", "Ин.10:9-16"),          # свт. Иоанн Тобольский
            date(2025, 1, 30): ("Утреня. Евангелие: Мф.11:27-30",      # прп. Антоний Великий
                                "Лк.6:17-23"),
            date(2025, 11, 29): ("1Кор.4:9-16", "Мф.9:9-13"),           # ап. Матфей
            date(2025, 9, 9): ("Мф.4:25-5:12",),                        # прп. Пимен
        }
        for day, expected in cases.items():
            t = get_reading(day).format()
            for e in expected:
                self.assertIn(e, t, day)
        # Местночтимые — с пометкой; при бдении и полиелее дня малые памяти не читаются.
        self.assertIn("если совершается служба", get_reading(date(2026, 8, 21)).format())
        self.assertNotIn("Кирика", get_reading(date(2025, 7, 28)).format())
        self.assertNotIn("Митрофана", get_reading(date(2025, 12, 6)).format())

    def test_vestments(self):
        # Цвет облачения — по таблице azbyka.ru (общий обычай Русской Церкви).
        cases = {
            date(2026, 10, 25): "gold",    # воскресенье
            date(2026, 4, 12): "red",      # Пасха
            date(2026, 5, 21): "white",    # Вознесение
            date(2026, 5, 31): "green",    # Троица
            date(2026, 3, 2): "black",     # будни Великого поста
            date(2026, 3, 8): "purple",    # Неделя Великого поста
            date(2026, 4, 4): "white",     # Лазарева суббота
            date(2026, 4, 5): "green",     # Вход Господень
            date(2026, 4, 9): "purple",    # Великий Четверг
            date(2026, 4, 10): "black",    # Великая Пятница
            date(2026, 1, 25): "white",    # попразднство Богоявления
            date(2026, 9, 27): "purple",   # Воздвижение
            date(2026, 10, 14): "blue",    # Покров
            date(2026, 9, 11): "red",      # Усекновение
            date(2026, 10, 8): "green",    # прп. Сергий
            date(2026, 5, 6): "red",       # вмч. Георгий в пасхальный период
        }
        for day, key in cases.items():
            self.assertEqual(get_reading(day).vestment.key, key, day)

    def test_triodion_table_complete(self):
        from src.readings import load_triodion
        t = load_triodion()
        for n in range(1, 71):
            self.assertTrue(t[str(n)]["readings"], n)
            for r in t[str(n)]["readings"]:
                for ref in [r.get("ref")] + [p["ref"] for p in r.get("parts", [])]:
                    if ref:
                        self.assertTrue(passage(ref), ref)

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
