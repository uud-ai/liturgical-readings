#!/usr/bin/env python3
"""Конвертация Синодального перевода из проекта Ponomar в data/bible/synodal.json.

Источник: https://github.com/typiconman/ponomar —
Ponomar/languages/cu/ru/bible/synod/*.text (формат: «#глава», затем «стих|текст»).

Использование:
    python tools/convert_ponomar_bible.py <путь к папке synod> data/bible/synodal.json

Результат: {"Быт": {"1": {"1": "В начале сотворил Бог небо и землю.", ...}, ...}, ...}
Курсив Синодального перевода (слова, добавленные переводчиками) сохраняется
тегами <i>…</i>. Строки без номера стиха (вводные тексты некоторых книг)
не включаются.
"""

import json
import re
import sys
from pathlib import Path

# Файлы Ponomar → сокращения, принятые в приложении (как в data/*.json).
BOOKS = [
    ("Gen", "Быт"), ("Ex", "Исх"), ("Lev", "Лев"), ("Num", "Чис"), ("Deut", "Втор"),
    ("Josh", "Нав"), ("Judg", "Суд"), ("Ruth", "Руфь"),
    ("I_Kings", "1Цар"), ("II_Kings", "2Цар"), ("III_Kings", "3Цар"), ("IV_Kings", "4Цар"),
    ("I_Paral", "1Пар"), ("II_Paral", "2Пар"), ("I_Esdra", "1Езд"), ("Nehem", "Неем"),
    ("II_Esdra", "2Езд"), ("Tobit", "Тов"), ("Judith", "Иудиф"), ("Esther", "Есф"),
    ("Job", "Иов"), ("Psalm", "Пс"), ("Prov", "Притч"), ("Eccles", "Еккл"), ("Song", "Песн"),
    ("Wisd", "Прем"), ("Sirach", "Сир"), ("Isa", "Ис"), ("Jerem", "Иер"), ("Lamen", "Плач"),
    ("Epistle", "ПослИер"), ("Baruch", "Вар"), ("Ezek", "Иез"), ("Dan", "Дан"),
    ("Hos", "Ос"), ("Joel", "Иоил"), ("Amos", "Ам"), ("Obad", "Авд"), ("Jona", "Иона"),
    ("Mica", "Мих"), ("Nahum", "Наум"), ("Habak", "Авв"), ("Zeph", "Соф"), ("Hagg", "Агг"),
    ("Zech", "Зах"), ("Mal", "Мал"), ("I_Macc", "1Мак"), ("II_Macc", "2Мак"),
    ("III_Macc", "3Мак"), ("III_Esdra", "3Езд"),
    ("Mt", "Мф"), ("Mk", "Мк"), ("Lk", "Лк"), ("Jn", "Ин"), ("Acts", "Деян"),
    ("Jas", "Иак"), ("I_Pet", "1Пет"), ("II_Pet", "2Пет"), ("I_Jn", "1Ин"), ("II_Jn", "2Ин"),
    ("III_Jn", "3Ин"), ("Jude", "Иуд"), ("Rom", "Рим"), ("I_Cor", "1Кор"), ("II_Cor", "2Кор"),
    ("Gal", "Гал"), ("Eph", "Еф"), ("Philip", "Флп"), ("Col", "Кол"), ("I_Thess", "1Фес"),
    ("II_Thess", "2Фес"), ("I_Tim", "1Тим"), ("II_Tim", "2Тим"), ("Tit", "Тит"),
    ("Philemon", "Флм"), ("Heb", "Евр"), ("Apoc", "Откр"),
]


def parse(path: Path) -> dict:
    chapters: dict[str, dict[str, str]] = {}
    chapter = None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        m = re.fullmatch(r"#(\d+)", line)
        if m:
            chapter = m.group(1)
            chapters[chapter] = {}
            continue
        m = re.match(r"(\d+)\|(.*)", line)
        if m and chapter:
            chapters[chapter][m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
    return chapters


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    bible = {}
    for fname, abbr in BOOKS:
        bible[abbr] = parse(src / f"{fname}.text")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bible, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    verses = sum(len(c) for b in bible.values() for c in b.values())
    print(f"{len(bible)} книг, {verses} стихов → {out}")


if __name__ == "__main__":
    main()
