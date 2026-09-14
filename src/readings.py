"""Логика получения чтений дня (Евангелие и Апостол по зачалам)."""

import json
from pathlib import Path
from datetime import date

from src.cycle import resolve_cycle_position

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_ordinary_cycle() -> dict:
    return _load("ordinary_cycle.json")


def load_pascha_dates() -> dict:
    return _load("pascha_dates.json")


def pick_pascha(day: date, pascha_dates: dict) -> date | None:
    """Выбрать дату Пасхи того литургического года, в который попадает day."""
    candidates = []
    for key, val in pascha_dates.items():
        if key.startswith("_"):
            continue
        candidates.append(date.fromisoformat(val["date"]))
    candidates.sort()
    chosen = None
    for pascha in candidates:
        if pascha <= day:
            chosen = pascha
        else:
            break
    return chosen


class Reading:
    def __init__(self, day: date, entry: dict | None, extra_note: str = ""):
        self.day = day
        self.entry = entry
        self.extra_note = extra_note

    @property
    def found(self) -> bool:
        return bool(self.entry)

    def format(self) -> str:
        header = f"Чтения на {self.day.strftime('%d.%m.%Y')}"
        if not self.found:
            msg = self.extra_note or "Данные для этой седмицы ещё не внесены."
            return f"{header}\n{msg}"

        lines = [header]
        if self.entry.get("note"):
            lines.append(self.entry["note"])

        apostle = self.entry.get("apostle")
        if apostle:
            z = self.entry.get("apostle_zachalo")
            suffix = f" (зач. {z})" if z else ""
            lines.append(f"Апостол: {apostle}{suffix}")

        gospel = self.entry.get("gospel")
        if gospel:
            z = self.entry.get("gospel_zachalo")
            suffix = f" (зач. {z})" if z else ""
            lines.append(f"Евангелие: {gospel}{suffix}")

        gm = self.entry.get("gospel_matins")
        if gm:
            if isinstance(gm, dict):
                ref = gm.get("ref")
                z = gm.get("zachalo", {}).get("number") if gm.get("zachalo") else None
            else:
                ref = gm
                z = self.entry.get("gospel_matins_zachalo")
            suffix = f" (зач. {z})" if z else ""
            lines.append(f"Евангелие утреннее: {ref}{suffix}")

        gv = self.entry.get("gospel_vespers")
        if gv:
            lines.append(f"Евангелие на вечерне: {gv}")

        return "\n".join(lines)


def get_reading(day: date) -> Reading:
    pascha_dates = load_pascha_dates()
    pascha = pick_pascha(day, pascha_dates)
    if pascha is None:
        return Reading(day, None, "Нет данных о дате Пасхи для этого периода.")

    pos = resolve_cycle_position(day, pascha)
    if pos.period == "unresolved":
        return Reading(
            day, None,
            "Эта дата попадает в период, который пока не реализован "
            "(Триодь постная / день Пятидесятницы / вне известных циклов)."
        )

    cycle = load_ordinary_cycle()
    week_table = cycle.get(pos.period, {}).get(pos.week)
    if not week_table:
        return Reading(
            day, None,
            f"Данные для этой седмицы ({pos.period}, неделя {pos.week}) "
            f"ещё не внесены — рядовые чтения для неё пока не собраны."
        )

    entry = week_table.get(pos.weekday)
    if not entry:
        return Reading(
            day, None,
            f"Данные для этого дня седмицы (неделя {pos.week}, {pos.weekday}) "
            f"ещё не внесены."
        )

    return Reading(day, entry)
