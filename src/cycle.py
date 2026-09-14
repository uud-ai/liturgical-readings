"""Определение положения даты в подвижном годовом круге чтений.

Мы НЕ вычисляем дату Пасхи сами (пасхалию) — берём её из проверенного
источника (data/pascha_dates.json). Дальше — только арифметика дат:
Пятидesyatница = Пасха + 49 дней; Неделя N по Пятидесятнице = Пятидесятница + 7N
дней; седмица N — шесть будних дней перед Неделей N.
"""

from dataclasses import dataclass
from datetime import date, timedelta

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class CyclePosition:
    period: str   # "pascha_period" | "pentecost_period" | "unresolved"
    week: str     # например "2", "13", или "pascha" для самого дня Пасхи
    weekday: str  # один из WEEKDAY_KEYS


def resolve_cycle_position(day: date, pascha: date) -> CyclePosition:
    pentecost = pascha + timedelta(days=49)

    if day < pascha:
        # До Пасхи текущего цикла — сюда же попадает Триодь постная,
        # которую мы пока не реализуем.
        return CyclePosition("unresolved", "", "")

    if pascha <= day < pentecost:
        days_since = (day - pascha).days
        if days_since == 0:
            return CyclePosition("pascha_period", "pascha", "sun")
        # Пасха сама по себе — вне нумерации; Неделя 2 (Фомина) — первая
        # пронумерованная неделя, поэтому здесь смещение +2, а не +1.
        week = (days_since - 1) // 7 + 2
        weekday = WEEKDAY_KEYS[(days_since - 1) % 7]
        return CyclePosition("pascha_period", str(week), weekday)

    if day == pentecost:
        return CyclePosition("pascha_period", "pentecost", "sun")

    if day > pentecost:
        days_since = (day - pentecost).days
        week = (days_since - 1) // 7 + 1
        weekday = WEEKDAY_KEYS[(days_since - 1) % 7]
        return CyclePosition("pentecost_period", str(week), weekday)

    return CyclePosition("unresolved", "", "")
