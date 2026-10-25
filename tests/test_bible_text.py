"""Текст Писания: разбор ссылок и полнота для всех чтений приложения."""

import json
import unittest

from src.bible_text import RefError, load_bible, parse_ref, passage
from src.cycle import DATA_DIR, eothinon


def all_refs():
    refs = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k.startswith("_"):
                    continue
                if k in ("ref", "apostle", "gospel", "gospel_matins", "gospel_vespers") \
                        and isinstance(v, str):
                    refs.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)

    for name in ("ordinary_cycle", "triodion", "feasts"):
        with open(DATA_DIR / f"{name}.json", encoding="utf-8") as f:
            walk(json.load(f))
    refs.update(eothinon(n)[1] for n in range(1, 12))
    return refs


class BibleTextTest(unittest.TestCase):
    def test_bible_complete(self):
        b = load_bible()
        self.assertEqual(len(b), 77)
        self.assertEqual(sum(len(c) for bk in b.values() for c in bk.values()), 37086)
        self.assertEqual(len(b["Пс"]), 151)
        self.assertIn("Прем", b)
        self.assertIn("Вар", b)

    def test_parse(self):
        self.assertEqual(parse_ref("Ин.13:31-18:1"), ("Ин", [(13, 31, 18, 1)]))
        self.assertEqual(parse_ref("Мк.5:22-24,35-43"), ("Мк", [(5, 22, 5, 24), (5, 35, 5, 43)]))
        self.assertEqual(parse_ref("Ин.7:37-52,8:12"), ("Ин", [(7, 37, 7, 52), (8, 12, 8, 12)]))

    def test_passages(self):
        v = passage("Ин.1:1-17")
        self.assertEqual(len(v), 17)
        self.assertTrue(v[0].text.startswith("В начале было Слово"))
        v = passage("Ин.13:31-18:1")              # через главы
        self.assertEqual((v[0].chapter, v[0].verse, v[-1].chapter, v[-1].verse), (13, 31, 18, 1))
        self.assertEqual(len(passage("Мк.5:22-24,35-43")), 3 + 9)
        self.assertTrue(passage("Прем.4:7-15"))   # неканонические книги
        self.assertTrue(passage("Вар.3:36-4:4"))
        with self.assertRaises(RefError):
            passage("Мф.29:1")

    def test_every_reading_has_text(self):
        bad = []
        for ref in all_refs():
            try:
                if not passage(ref):
                    bad.append(ref)
            except RefError as exc:
                bad.append(str(exc))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
