"""Цвет богослужебных облачений дня (общий обычай Русской Церкви).

Источник правил — таблица «Цвета богослужебных облачений» и статья «Цвет
облачения» на azbyka.ru; где таблица допускает два цвета, берётся первый.
Местная практика может отличаться, поэтому приложение подаёт цвет как
справку, а не как предписание.

Порядок старшинства:
1. Пасхальный период — красный; Вознесение с попразднством — белый;
   Пятидесятница с попразднством — зелёный.
2. Двунадесятые и великие праздники в самый день.
3. Лазарева суббота — белый, Вход Господень — зелёный, Страстная седмица —
   чёрный (Великий Четверг — фиолетовый, Великая Суббота — белый).
4. Память святого с бдением или полиелеем в будни (в т. ч. в Великий пост) —
   по чину святого (поле vestment в data/feasts.json); в воскресенье — золотой.
5. Великий пост: субботы и воскресенья — фиолетовый, будни — чёрный.
6. Предпразднства и попразднства: Рождество (с навечерия), Богоявление (со
   2 января ст. ст.), Преображение — белый; Воздвижение, Происхождение
   Честных Древ — фиолетовый.
7. Остальные дни — золотой.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.cycle import pascha


@dataclass(frozen=True)
class Vestment:
    key: str     # gold | white | red | blue | green | purple | black
    name: str    # «золотое» — согласуется со словом «облачение»


VESTMENTS = {
    "gold": Vestment("gold", "золотое"),
    "white": Vestment("white", "белое"),
    "red": Vestment("red", "красное"),
    "blue": Vestment("blue", "голубое"),
    "green": Vestment("green", "зелёное"),
    "purple": Vestment("purple", "фиолетовое"),
    "black": Vestment("black", "чёрное"),
}

# Праздники в самый день (дата по старому стилю).
FEAST_DAY = {
    "12-24": "white", "12-25": "white", "01-01": "white", "01-05": "white",
    "01-06": "white", "02-02": "blue", "03-25": "blue", "06-24": "gold",
    "06-29": "gold", "08-01": "purple", "08-06": "white", "08-15": "blue",
    "08-29": "red", "09-08": "blue", "09-14": "purple", "10-01": "blue",
    "11-21": "blue", "12-26": "white",
}

# Предпразднства и попразднства (включительно, старый стиль).
FEAST_PERIODS = [
    ("12-24", "12-31", "white"),     # навечерие и попразднство Рождества
    ("01-02", "01-14", "white"),     # предпразднство и попразднство Богоявления
    ("08-06", "08-13", "white"),     # Преображение
    ("09-14", "09-21", "purple"),    # Воздвижение
]


def _old_key(day: date) -> str:
    o = day - timedelta(days=13)
    return f"{o.month:02d}-{o.day:02d}"


def vestment(reading) -> Vestment:
    return VESTMENTS[_vestment_key(reading)]


def _vestment_key(reading) -> str:
    day = reading.day
    wd = day.weekday()
    key = _old_key(day)

    p = pascha(day.year)
    n = (day - p).days
    if 0 <= n <= 38:
        return "red"
    if 39 <= n <= 47:
        return "white"
    if 49 <= n <= 55:
        return "green"

    if key in FEAST_DAY:
        return FEAST_DAY[key]

    t = reading.pos.triodion_day
    if t:
        if t == 8:
            return "white"            # Лазарева суббота
        if t == 7:
            return "green"            # Вход Господень в Иерусалим
        if t <= 6:
            return {3: "purple", 1: "white"}.get(t, "black")

    if wd < 6:
        for c in reading.memories:
            if c.get("rank") in ("vigil", "polyeleos") and not c.get("conditional"):
                return c.get("vestment", "gold")

    if t and t <= 48:
        return "purple" if wd >= 5 else "black"

    for start, end, color in FEAST_PERIODS:
        if start <= key <= end:
            return color
    return "gold"
