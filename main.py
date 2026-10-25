#!/usr/bin/env python3
"""Вывести евангельское и апостольское чтение дня.

Использование:
    python main.py                       # чтения на сегодня
    python main.py 2026-09-14            # чтения на конкретную дату
    python main.py 2026-09-14 --text     # то же с полным текстом чтений
"""

import sys
from datetime import date

from src.readings import get_reading


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    try:
        day = date.fromisoformat(args[0]) if args else date.today()  # noqa: DTZ011
        print(get_reading(day).format(with_text="--text" in sys.argv))
    except ValueError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
