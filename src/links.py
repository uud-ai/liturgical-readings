"""Ссылки на текст чтений на azbyka.ru (Синодальный перевод).

Коды книг взяты со страниц azbyka.ru/biblia (проверено 25.10.2026).
"""

from __future__ import annotations

from datetime import date

AZBYKA_BOOKS = {
    "Мф": "Mt", "Мк": "Mk", "Лк": "Lk", "Ин": "Jn", "Деян": "Act",
    "Иак": "Jac", "1Пет": "1Pet", "2Пет": "2Pet", "1Ин": "1Jn", "2Ин": "2Jn",
    "3Ин": "3Jn", "Иуд": "Juda", "Рим": "Rom", "1Кор": "1Cor", "2Кор": "2Cor",
    "Гал": "Gal", "Еф": "Eph", "Флп": "Phil", "Кол": "Col", "1Фес": "1Thes",
    "2Фес": "2Thes", "1Тим": "1Tim", "2Тим": "2Tim", "Тит": "Tit",
    "Флм": "Phlm", "Евр": "Hebr",
    # Ветхий Завет (паремии)
    "Быт": "Gen", "Исх": "Ex", "Нав": "Nav", "3Цар": "1King", "4Цар": "2King",
    "Иов": "Job", "Притч": "Prov", "Ис": "Is", "Иер": "Jer", "Иез": "Ezek",
    "Дан": "Dan", "Иоил": "Joel", "Ам": "Am", "Иона": "Jona", "Соф": "Sofon",
    "Зах": "Zah", "Вар": "Bar", "Лев": "Lev", "Мих": "Mic", "Суд": "Judg",
    "Чис": "Num",
}


def bible_url(ref: str) -> str | None:
    """«Лк.7:11-16» → https://azbyka.ru/biblia/?Lk.7:11-16"""
    book, _, rest = ref.replace(" ", "").partition(".")
    code = AZBYKA_BOOKS.get(book)
    if not code or not rest:
        return None
    return f"https://azbyka.ru/biblia/?{code}.{rest}"


def day_url(day: date) -> str:
    """Страница всех чтений дня (с праздничными и святыми) на azbyka.ru."""
    return f"https://azbyka.ru/biblia/days/{day.isoformat()}"
