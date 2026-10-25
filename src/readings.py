"""Получение чтений дня (Евангелие и Апостол по зачалам)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from src.cycle import DATA_DIR, DayPosition, Slot, eothinon, resolve
from src.links import bible_url, day_url


@lru_cache(maxsize=1)
def load_ordinary_cycle() -> dict:
    with open(DATA_DIR / "ordinary_cycle.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_triodion() -> dict:
    with open(DATA_DIR / "triodion.json", encoding="utf-8") as f:
        return json.load(f)


def lookup(slot: Slot | None) -> dict | None:
    if slot is None:
        return None
    week = load_ordinary_cycle().get(slot.period, {}).get(slot.week) or {}
    return week.get(slot.weekday) or None


def _week_label(slot: Slot) -> str:
    if slot.period == "pentecost_period":
        return f"{slot.week}-й седмицы по Пятидесятнице"
    return f"{slot.week}-й седмицы по Пасхе"


@dataclass
class Part:
    """Часть составного чтения."""
    ref: str
    zachalo: str = ""

    @property
    def url(self) -> str | None:
        return bible_url(self.ref)

    def text(self) -> str:
        return self.ref + (f" (зач. {self.zachalo})" if self.zachalo else "")


@dataclass
class Item:
    """Одно чтение дня."""
    kind: str          # apostle | gospel | matins | vespers | triodion
    label: str         # «Апостол», «Евангелие», «Паремия 1-я», …
    ref: str = ""      # «Лк.7:11-16»; пусто, если чтение не внесено
    zachalo: str = ""  # «30», «130 от полу»
    missing: str = ""  # пояснение, если ref пуст
    service: str = ""  # «Литургия», «Утреня», «6-й час», …
    parts: list[Part] = field(default_factory=list)  # для составных чтений

    @property
    def url(self) -> str | None:
        return bible_url(self.ref) if self.ref else None

    def text(self) -> str:
        label = f"{self.service}. {self.label}" if self.kind == "triodion" else self.label
        if self.parts:
            return f"{label}: " + "; ".join(p.text() for p in self.parts)
        if not self.ref:
            return f"{label}: {self.missing}"
        z = f" (зач. {self.zachalo})" if self.zachalo else ""
        return f"{label}: {self.ref}{z}"


class Reading:
    def __init__(self, day: date, pos: DayPosition):
        self.day = day
        self.pos = pos
        self.apostle_entry = lookup(pos.apostle) or {}
        self.gospel_entry = lookup(pos.gospel) or {}
        self.notes = [pos.unresolved] if pos.unresolved else list(pos.notes)
        if pos.triodion_day:
            entry = load_triodion()[str(pos.triodion_day)]
            self.title, self.note = entry["title"], ""
            self.items = self._triodion_items(entry)
            if entry.get("note"):
                self.notes.insert(0, entry["note"])
        else:
            self.title, self.note = self._title_and_note()
            self.items = [] if pos.unresolved else self._items()

    @property
    def found(self) -> bool:
        return any(i.ref for i in self.items)

    @property
    def groups(self) -> list[tuple[str, list[Item]]]:
        """Чтения, сгруппированные по службам в порядке появления."""
        out: list[tuple[str, list[Item]]] = []
        for item in self.items:
            if out and out[-1][0] == item.service:
                out[-1][1].append(item)
            else:
                out.append((item.service, [item]))
        return out

    @property
    def azbyka_day_url(self) -> str:
        return day_url(self.day)

    def _title_and_note(self) -> tuple[str, str]:
        title = self.pos.title
        if self.pos.unresolved:
            return title, ""
        same_slot = self.pos.apostle == self.pos.gospel
        note = self.apostle_entry.get("note", "") if same_slot else ""
        if note.startswith(("Неделя", "Светлое", "День Святой")):
            return note, ""
        return title, note

    def _items(self) -> list[Item]:
        a, g = self.apostle_entry, self.gospel_entry
        items = []
        for kind, label, entry, slot in (
                ("apostle", "Апостол", a, self.pos.apostle),
                ("gospel", "Евангелие", g, self.pos.gospel)):
            ref = entry.get(kind)
            if ref:
                items.append(Item(kind, label, ref, str(entry.get(f"{kind}_zachalo") or ""),
                                  service="Литургия"))
            else:
                items.append(Item(kind, label, service="Литургия", missing=(
                    f"рядовое чтение {_week_label(slot)} ещё не внесено.")))

        gm = a.get("gospel_matins")
        if isinstance(gm, dict):
            ref, z = gm.get("ref"), (gm.get("zachalo") or {}).get("number")
        else:
            ref, z = gm, a.get("gospel_matins_zachalo")
        if ref:
            items.insert(0, Item("matins", "Евангелие утреннее", ref, str(z or ""),
                                 service="Утреня"))
        elif self.pos.sunday_after_pentecost:
            n, ref, z = eothinon(self.pos.sunday_after_pentecost)
            items.insert(0, Item("matins", f"Евангелие утреннее ({n}-е воскресное)",
                                 ref, str(z), service="Утреня"))

        if a.get("gospel_vespers"):
            items.append(Item("vespers", "Евангелие на вечерне", a["gospel_vespers"],
                              service="Вечерня"))
        return items

    def _triodion_items(self, entry: dict) -> list[Item]:
        items = []
        if self.pos.sunday_after_pentecost:
            n, ref, z = eothinon(self.pos.sunday_after_pentecost)
            items.append(Item("triodion", f"Евангелие {n}-е воскресное", ref,
                              str(z), service="Утреня"))
        for r in entry["readings"]:
            items.append(Item(
                "triodion", r["label"], r.get("ref", ""), str(r.get("zachalo", "")),
                service=r["service"],
                parts=[Part(p["ref"], str(p.get("zachalo", ""))) for p in r.get("parts", [])]))
        return items

    def format(self) -> str:
        lines = [f"Чтения на {self.day.strftime('%d.%m.%Y')}"]
        if not self.pos.unresolved:
            lines.append(self.title)
            if self.note:
                lines.append(self.note)
        # В тексте порядок привычный: Апостол, Евангелие, затем утреннее.
        order = {"apostle": 0, "gospel": 1, "matins": 2, "vespers": 3, "triodion": 4}
        lines += [i.text() for i in sorted(self.items, key=lambda i: order[i.kind])]
        lines += self.notes
        return "\n".join(lines)


def get_reading(day: date) -> Reading:
    return Reading(day, resolve(day))
