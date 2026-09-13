"""Логика получения чтений дня (Евангелие и Апостол по зачалам)."""

import json
from pathlib import Path
from datetime import date

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    path = DATA_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gospel_zachala() -> dict:
    return _load("gospel_zachala.json")


def load_apostle_zachala() -> dict:
    return _load("apostle_zachala.json")


def load_readings_calendar() -> dict:
    return _load("readings_calendar.json")


class Reading:
    """Чтения дня: евангельское и апостольское зачало с текстом (если есть)."""

    def __init__(self, day: date, entry: dict | None,
                 gospel_zachala: dict, apostle_zachala: dict):
        self.day = day
        self.entry = entry
        self.gospel_zachala = gospel_zachala
        self.apostle_zachala = apostle_zachala

    @property
    def found(self) -> bool:
        return self.entry is not None

    def _gospel_info(self):
        if not self.entry:
            return None
        g = self.entry.get("gospel")
        if not g:
            return None
        book, number = g["book"], str(g["number"])
        return self.gospel_zachala.get(book, {}).get(number)

    def _apostle_info(self):
        if not self.entry:
            return None
        a = self.entry.get("apostle")
        if not a:
            return None
        number = str(a["number"])
        return self.apostle_zachala.get(number)

    def format(self) -> str:
        header = f"Чтения на {self.day.strftime('%d.%m.%Y')}"
        if not self.found:
            return (
                f"{header}\n"
                f"Данные для этой даты ещё не внесены в readings_calendar.json."
            )

        lines = [header]
        note = self.entry.get("note")
        if note:
            lines.append(note)

        gospel = self._gospel_info()
        if gospel:
            lines.append(f"Евангелие: {gospel['ref']}")
            if gospel.get("text"):
                lines.append(gospel["text"])
            else:
                lines.append("  (текст зачала пока не внесён)")

        apostle = self._apostle_info()
        if apostle:
            lines.append(f"Апостол: {apostle['ref']}")
            if apostle.get("text"):
                lines.append(apostle["text"])
            else:
                lines.append("  (текст зачала пока не внесён)")

        return "\n".join(lines)


def get_reading(day: date) -> Reading:
    calendar = load_readings_calendar()
    entry = calendar.get(day.isoformat())
    gospel_zachala = load_gospel_zachala()
    apostle_zachala = load_apostle_zachala()
    return Reading(day, entry, gospel_zachala, apostle_zachala)
