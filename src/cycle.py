"""Положение даты в подвижном годовом круге чтений.

Дата Пасхи берётся из data/pascha_dates.json (проверенные даты), а для лет,
которых там нет, вычисляется по юлианской пасхалии (алгоритм Меёса) с
переводом в новый стиль (+13 дней; верно для 1900–2099 гг.). Дальше —
арифметика дат:

* Пятидесятница = Пасха + 49 дней; Неделя N по Пятидесятнице =
  Пятидесятница + 7N дней; седмица N — шесть будних дней перед Неделей N.
* Апостол читается по счёту седмиц от Пятидесятницы.
* Евангелие со дня после Недели по Воздвижении читается от Луки, начиная
  с рядового Евангелия 18-й седмицы, независимо от счёта седмиц
  (Воздвиженская отступка/преступка).
* От Недели святых отец перед Рождеством до Недели о Закхее действуют
  особые правила (рождественская и крещенская отступки) — не реализовано,
  приложение честно сообщает об этом.
* С Недели о Закхее (за 77 дней до следующей Пасхи) чтения отсчитываются
  назад от следующей Пасхи: Неделя о Закхее — 32-я, будни после неё — 33-я.
* С Недели о мытаре и фарисее (за 70 дней до Пасхи) начинается Триодь
  постная — она не реализована.

Праздничные и святые чтения сознательно не реализованы; для воскресений,
когда устав заменяет рядовые чтения (пред и по Воздвижении, праотец),
выводится предупреждение.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_RU = ["понедельник", "вторник", "среда", "четверг", "пятница",
              "суббота", "воскресенье"]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Воздвижение 14/27 сентября (новый стиль, 1900–2099).
ELEVATION = (9, 27)

# Последняя седмица, чтения которой берутся по прямому счёту для Апостола.
LAST_FORWARD_APOSTLE_SUNDAY = 32
# Седмица, с которой Евангелие читается от Луки (Лк 3:19-22, зач. 10).
FIRST_LUKE_WEEK = 18


@dataclass(frozen=True)
class Slot:
    """Ячейка таблицы ordinary_cycle.json."""
    period: str   # "pascha_period" | "pentecost_period"
    week: str     # "2".."8", "pascha", "pentecost" или номер седмицы по Пятидесятнице
    weekday: str  # один из WEEKDAY_KEYS


@dataclass
class DayPosition:
    title: str
    apostle: Slot | None = None
    gospel: Slot | None = None
    sunday_after_pentecost: int | None = None  # номер Недели по Пятидесятнице
    notes: list[str] = field(default_factory=list)
    unresolved: str = ""  # непустая строка — день вне реализованной части


# --- Пасхалия -------------------------------------------------------------

def computed_pascha(year: int) -> date:
    """Православная Пасха (юлианская пасхалия), дата по новому стилю."""
    if not 1900 <= year <= 2099:
        raise ValueError("Пасхалия реализована для 1900–2099 гг.")
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return date(year, month, day) + timedelta(days=13)


@lru_cache(maxsize=1)
def _known_pascha_dates() -> dict[int, date]:
    with open(DATA_DIR / "pascha_dates.json", encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): date.fromisoformat(v["date"])
            for k, v in raw.items() if not k.startswith("_")}


def pascha(year: int) -> date:
    return _known_pascha_dates().get(year) or computed_pascha(year)


# --- Вспомогательные даты --------------------------------------------------

def _sunday_after(d: date) -> date:
    """Ближайшее воскресенье строго после d."""
    return d + timedelta(days=(6 - d.weekday()) % 7 or 7)


def _sunday_before(d: date) -> date:
    """Ближайшее воскресенье строго до d."""
    return d - timedelta(days=(d.weekday() + 1) % 7 or 7)


def _week_and_day(day: date, anchor: date) -> tuple[int, str]:
    """Номер «седмицы» и день недели относительно anchor (воскресенья)."""
    n = (day - anchor).days
    return (n - 1) // 7 + 1, WEEKDAY_KEYS[(n - 1) % 7]


# --- Основной расчёт ------------------------------------------------------

def resolve(day: date) -> DayPosition:
    this_pascha = pascha(day.year)
    if day < this_pascha:
        this_pascha = pascha(day.year - 1)
    next_pascha = pascha(this_pascha.year + 1)
    pentecost = this_pascha + timedelta(days=49)

    if day >= next_pascha - timedelta(days=70):
        return DayPosition(
            title="Период Триоди постной",
            unresolved="Дата попадает в период Триоди постной (от Недели о "
                       "мытаре и фарисее до Пасхи) — он пока не реализован.")

    if day == this_pascha:
        s = Slot("pascha_period", "pascha", "sun")
        return DayPosition("Светлое Христово Воскресение", s, s)

    if day < pentecost:
        days = (day - this_pascha).days
        week = (days - 1) // 7 + 2
        wd = WEEKDAY_KEYS[(days - 1) % 7]
        if week == 2 and wd != "sun":
            title = f"Светлая седмица, {WEEKDAY_RU[WEEKDAY_KEYS.index(wd)]}"
        elif wd == "sun":
            title = f"Неделя {week}-я по Пасхе"
        else:
            title = (f"Седмица {week - 1}-я по Пасхе, "
                     f"{WEEKDAY_RU[WEEKDAY_KEYS.index(wd)]}")
        s = Slot("pascha_period", str(week), wd)
        return DayPosition(title, s, s)

    if day == pentecost:
        s = Slot("pascha_period", "pentecost", "sun")
        return DayPosition("День Святой Троицы. Пятидесятница", s, s)

    # --- период по Пятидесятнице ---
    week, wd = _week_and_day(day, pentecost)
    is_sunday = wd == "sun"
    if is_sunday:
        title = f"Неделя {week}-я по Пятидесятнице"
    else:
        title = (f"Седмица {week}-я по Пятидесятнице, "
                 f"{WEEKDAY_RU[WEEKDAY_KEYS.index(wd)]}")
    pos = DayPosition(title, sunday_after_pentecost=week if is_sunday else None)

    # Обратный счёт от следующей Пасхи: Неделя о мытаре = «33-я» Неделя.
    virtual_pentecost = next_pascha - timedelta(days=70 + 7 * 33)
    back_week, back_wd = _week_and_day(day, virtual_pentecost)
    assert back_wd == wd

    elevation = date(pentecost.year, *ELEVATION)
    sun_before_elevation = _sunday_before(elevation)
    sun_after_elevation = _sunday_after(elevation)
    # Неделя святых праотец (11–17 декабря ст. ст.) и Неделя святых отец
    # перед Рождеством (18–24 декабря ст. ст.).
    forefathers = _sunday_after(date(pentecost.year, 12, 23))
    fathers_before_nativity = forefathers + timedelta(days=7)
    zacchaeus = next_pascha - timedelta(days=77)

    # С Недели о Закхее чтения всегда берутся по обратному счёту:
    # Неделя о Закхее — 32-я, будни перед Триодью — 33-я седмица.
    from_zacchaeus = day >= zacchaeus

    if not from_zacchaeus and day >= fathers_before_nativity:
        pos.unresolved = (
            "Период от Недели святых отец перед Рождеством до Недели о Закхее: "
            "рядовые чтения здесь определяются особыми правилами (рождественская "
            "и крещенская отступки, перенос пропущенных воскресных Евангелий) — "
            "пока не реализовано, смотрите богослужебные указания.")
        return pos

    if from_zacchaeus:
        apostle_week = gospel_week = back_week
    else:
        # Апостол — по счёту от Пятидесятницы. После 32-й Недели (возможно
        # в годы с поздней следующей Пасхой) — обратный счёт, как в orthocal.
        past_32nd_sunday = (week > LAST_FORWARD_APOSTLE_SUNDAY
                            or (week == LAST_FORWARD_APOSTLE_SUNDAY and is_sunday))
        apostle_week = back_week if past_32nd_sunday else week
        # Евангелие — от Луки с понедельника после Недели по Воздвижении.
        if day > sun_after_elevation:
            first_luke_monday = sun_after_elevation + timedelta(days=1)
            gospel_week = week + FIRST_LUKE_WEEK - _week_and_day(
                first_luke_monday, pentecost)[0]
        else:
            gospel_week = week

    pos.apostle = Slot("pentecost_period", str(apostle_week), wd)
    pos.gospel = Slot("pentecost_period", str(gospel_week), wd)

    special_sundays = {
        sun_before_elevation: "Неделя пред Воздвижением: Гал. 6:11–18; Ин. 3:13–17",
        sun_after_elevation: "Неделя по Воздвижении: Гал. 2:16–20; Мк. 8:34–9:1",
        forefathers: "Неделя святых праотец: Кол. 3:4–11; Лк. 14:16–24",
    }
    if day in special_sundays:
        pos.notes.append(
            f"{special_sundays[day]} — по уставу эти чтения читаются вместо "
            f"рядовых (праздничные чтения в приложении не реализованы).")
    if apostle_week != week:
        pos.notes.append(f"Апостол — рядовой {apostle_week}-й седмицы "
                         f"(счёт назад от Недели о мытаре и фарисее).")
    if gospel_week != week:
        if from_zacchaeus:
            reason = "счёт назад от Недели о мытаре и фарисее"
        elif gospel_week < week:
            reason = "Воздвиженская отступка"
        else:
            reason = "Воздвиженская преступка"
        pos.notes.append(f"Евангелие — рядовое {gospel_week}-й седмицы ({reason}).")
    return pos


# Цикл воскресных утренних (евангелий утренних, «столпов»).
EOTHINA = [
    ("Мф.28:16-20", 116), ("Мк.16:1-8", 70), ("Мк.16:9-20", 71),
    ("Лк.24:1-12", 112), ("Лк.24:12-35", 113), ("Лк.24:36-53", 114),
    ("Ин.20:1-10", 63), ("Ин.20:11-18", 64), ("Ин.20:19-31", 65),
    ("Ин.21:1-14", 66), ("Ин.21:15-25", 67),
]


def eothinon(sunday_after_pentecost: int) -> tuple[int, str, int]:
    """Номер, ссылка и зачало воскресного утреннего Евангелия.

    Неделя Всех святых (1-я по Пятидесятнице) — 1-е утреннее, далее по
    порядку с циклом 11 недель.
    """
    n = (sunday_after_pentecost - 1) % 11
    ref, zach = EOTHINA[n]
    return n + 1, ref, zach
