"""Получение чтений дня (Евангелие и Апостол по зачалам)."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from src.cycle import DATA_DIR, DayPosition, Slot, eothinon, resolve


@lru_cache(maxsize=1)
def load_ordinary_cycle() -> dict:
    with open(DATA_DIR / "ordinary_cycle.json", encoding="utf-8") as f:
        return json.load(f)


def lookup(slot: Slot | None) -> dict | None:
    if slot is None:
        return None
    week = load_ordinary_cycle().get(slot.period, {}).get(slot.week) or {}
    return week.get(slot.weekday) or None


def _zach(z) -> str:
    return f" (зач. {z})" if z else ""


def _week_label(slot: Slot) -> str:
    if slot.period == "pentecost_period":
        return f"{slot.week}-й седмицы по Пятидесятнице"
    return f"{slot.week}-й седмицы по Пасхе"


class Reading:
    def __init__(self, day: date, pos: DayPosition):
        self.day = day
        self.pos = pos
        self.apostle_entry = lookup(pos.apostle)
        self.gospel_entry = lookup(pos.gospel)

    @property
    def found(self) -> bool:
        return bool(self.apostle_entry or self.gospel_entry)

    def _title_and_note(self) -> tuple[str, str]:
        title = self.pos.title
        same_slot = self.pos.apostle == self.pos.gospel
        note = (self.apostle_entry or {}).get("note", "") if same_slot else ""
        if note.startswith(("Неделя", "Светлое", "День Святой")):
            return note, ""
        return title, note

    def format(self) -> str:
        lines = [f"Чтения на {self.day.strftime('%d.%m.%Y')}"]
        if self.pos.unresolved:
            lines.append(self.pos.unresolved)
            return "\n".join(lines)

        title, note = self._title_and_note()
        lines.append(title)
        if note:
            lines.append(note)

        a = self.apostle_entry or {}
        if a.get("apostle"):
            lines.append(f"Апостол: {a['apostle']}{_zach(a.get('apostle_zachalo'))}")
        else:
            lines.append(f"Апостол: рядовое чтение {_week_label(self.pos.apostle)} "
                         f"ещё не внесено.")

        g = self.gospel_entry or {}
        if g.get("gospel"):
            lines.append(f"Евангелие: {g['gospel']}{_zach(g.get('gospel_zachalo'))}")
        else:
            lines.append(f"Евангелие: рядовое чтение {_week_label(self.pos.gospel)} "
                         f"ещё не внесено.")

        gm = a.get("gospel_matins")
        if isinstance(gm, dict):
            ref = gm.get("ref")
            z = (gm.get("zachalo") or {}).get("number")
        else:
            ref, z = gm, a.get("gospel_matins_zachalo")
        if ref:
            lines.append(f"Евангелие утреннее: {ref}{_zach(z)}")
        elif self.pos.sunday_after_pentecost:
            n, ref, z = eothinon(self.pos.sunday_after_pentecost)
            lines.append(f"Евангелие утреннее ({n}-е воскресное): {ref}{_zach(z)}")

        if a.get("gospel_vespers"):
            lines.append(f"Евангелие на вечерне: {a['gospel_vespers']}")

        lines.extend(self.pos.notes)
        return "\n".join(lines)


def get_reading(day: date) -> Reading:
    return Reading(day, resolve(day))
