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
* После Богоявления (Крещенская отступка) будни читаются по обратному счёту
  от следующей Пасхи. Воскресенья между Неделей по Богоявлении и Неделей
  о Закхее заполняются назад от Закхея пропущенными воскресными чтениями:
  31-й Недели (о слепом), 30-й (о богатом начальнике); если таких воскресений
  три — перед Закхеем ещё 17-я (о хананеянке). Если они есть, в Неделю по
  Богоявлении рядовые не читаются; если нет — читаются под зачало (31-я).
  Правило — «Сказание» напрестольного Евангелия; порядок сверен с azbyka.ru
  (2013, 2019, 2022, 2024, 2025 гг.).
* В год с Воздвиженской отступкой с субботы пред Рождеством Христовым Апостол
  читается по седмице Евангелия; если рядовые седмицы исчерпаны до
  Богоявления (ранняя Пасха), читается 33-я седмица (сверено с azbyka.ru:
  2011, 2016, 2018 гг.).
* С Недели о Закхее (за 77 дней до следующей Пасхи) чтения отсчитываются
  назад от следующей Пасхи: Неделя о Закхее — 32-я, будни после неё — 33-я.
* С Недели о мытаре и фарисее (за 70 дней до Пасхи) до Великой Субботы —
  Триодь постная: чтения по таблице data/triodion.json (по числу дней
  до Пасхи).

Праздничные и святые чтения накладываются на рядовые в src/readings.py.
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

# Воздвижение 14/27 сентября, Богоявление 6/19 января (новый стиль, 1900–2099).
ELEVATION = (9, 27)
THEOPHANY = (1, 19)

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
    ordinary_omitted: bool = False  # рядовые чтения в этот день не читаются
    triodion_day: int | None = None  # дней до Пасхи (70 … 1) в период Триоди


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
        # Триодь постная: от Недели о мытаре и фарисее до Великой Субботы.
        n = (next_pascha - day).days
        pos = DayPosition(title="", triodion_day=n)
        if day.weekday() == 6 and n >= 14:
            # Цикл евангелий утренних продолжается от Пятидесятницы
            # до Недели 5-й Великого поста; в Неделю ваий — своё Евангелие.
            pos.sunday_after_pentecost = (day - pentecost).days // 7
        return pos

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
    sun_after_elevation = _sunday_after(elevation)
    zacchaeus = next_pascha - timedelta(days=77)
    theophany = date(pentecost.year + 1, *THEOPHANY)

    # С Недели о Закхее чтения всегда берутся по обратному счёту:
    # Неделя о Закхее — 32-я, будни перед Триодью — 33-я седмица.
    from_zacchaeus = day >= zacchaeus
    # После Богоявления — Крещенская отступка: тоже обратный счёт.
    after_theophany = day > theophany

    if from_zacchaeus or after_theophany:
        if after_theophany and is_sunday and not from_zacchaeus:
            sunday_after_theophany = _sunday_after(theophany)
            gap = (zacchaeus - sunday_after_theophany).days // 7 - 1
            if day == sunday_after_theophany:
                if gap > 0:
                    pos.ordinary_omitted = True
                    pos.notes.append(
                        "Крещенская отступка: в Неделю по Богоявлении рядовые чтения не "
                        "читаются — пропущенные воскресные чтения переносятся на следующие "
                        "Недели.")
                    return pos
            else:
                order = ([17] if gap >= 3 else []) + [31, 30]
                n = order[(zacchaeus - day).days // 7 - 1]
                pos.apostle = pos.gospel = Slot("pentecost_period", str(n), wd)
                pos.notes.append(
                    f"Крещенская отступка: читаются Апостол и Евангелие Недели {n}-й по "
                    f"Пятидесятнице.")
                return pos
        apostle_week = gospel_week = back_week
    else:
        # Апостол — по счёту от Пятидесятницы.
        past_32nd_sunday = week > LAST_FORWARD_APOSTLE_SUNDAY
        apostle_week = week
        # Евангелие — от Луки с понедельника после Недели по Воздвижении.
        if day > sun_after_elevation:
            first_luke_monday = sun_after_elevation + timedelta(days=1)
            gospel_week = week + FIRST_LUKE_WEEK - _week_and_day(
                first_luke_monday, pentecost)[0]
        else:
            gospel_week = week
        # Неделя святых отец пред Рождеством (18–24 декабря ст. ст.).
        fathers_sunday = _sunday_after(date(pentecost.year, 12, 30))
        if is_sunday and day >= fathers_sunday:
            # Недели святых отец, по Рождестве, пред Богоявлением (и праздники в эти
            # дни): рядовые чтения не читаются — воскресные Евангелия Луки берегутся
            # для воскресений после Богоявления.
            pos.ordinary_omitted = True
            return pos
        if day >= fathers_sunday - timedelta(days=1) and gospel_week < week:
            # Год с отступкой: с субботы пред Рождеством Апостол возвращается
            # к седмице Евангелия (azbyka.ru: 2011, 2016 гг.).
            apostle_week = gospel_week
            pos.notes.append(
                f"Год с Воздвиженской отступкой: с субботы пред Рождеством Христовым "
                f"Апостол и Евангелие читаются рядовые {gospel_week}-й седмицы.")
        elif past_32nd_sunday:
            # Ранняя Пасха: рядовые седмицы исчерпаны до Богоявления — читается
            # 33-я седмица (повторяется перед Неделей о мытаре; azbyka.ru, 2018 г.).
            pos.notes.append(
                "Рядовые седмицы этого года исчерпаны до Богоявления: читаются чтения "
                "33-й седмицы (они повторятся перед Неделей о мытаре и фарисее).")
        if apostle_week > 33 or gospel_week > 33:
            pos.notes.clear()
            pos.unresolved = (
                "Рядовые седмицы этого года исчерпаны до Богоявления: порядок рядовых "
                "чтений до Богоявления определяется особыми правилами — пока не "
                "реализовано, смотрите богослужебные указания.")
            return pos
        if pos.notes:
            pos.apostle = Slot("pentecost_period", str(apostle_week), wd)
            pos.gospel = Slot("pentecost_period", str(gospel_week), wd)
            return pos

    pos.apostle = Slot("pentecost_period", str(apostle_week), wd)
    pos.gospel = Slot("pentecost_period", str(gospel_week), wd)
    if not (from_zacchaeus or after_theophany) and day <= sun_after_elevation \
            and gospel_week >= FIRST_LUKE_WEEK:
        # Год с отступкой: Матфеевы седмицы кончились, а Лукины ещё не начались —
        # рядовое Евангелие берётся из уже прочитанных Матфеевых (azbyka.ru, 2026 г.).
        pos.gospel = None
        pos.notes.append("Год с Воздвиженской отступкой: до понедельника после Недели по "
                         "Воздвижении рядовое Евангелие берётся из Матфеевых седмиц — "
                         "смотрите богослужебные указания.")
        return pos

    if apostle_week != week:
        pos.notes.append(f"Апостол — рядовой {apostle_week}-й седмицы "
                         f"(счёт назад от Недели о мытаре и фарисее).")
    if gospel_week != week:
        if from_zacchaeus or after_theophany:
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
