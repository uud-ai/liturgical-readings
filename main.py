#!/usr/bin/env python3
"""Вывести евангельское и апостольское чтение дня.

Использование:
    python main.py                # чтения на сегодня
    python main.py 2026-09-14     # чтения на конкретную дату
"""

import sys
from datetime import date

from src.readings import get_reading


def parse_date(argv: list[str]) -> date:
    if len(argv) < 2:
        return date.today()
    return date.fromisoformat(argv[1])


def main() -> None:
    day = parse_date(sys.argv)
    reading = get_reading(day)
    print(reading.format())


if __name__ == "__main__":
    main()
