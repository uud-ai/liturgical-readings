"""Текст чтений по ссылке вида «Мф.4:25-5:12», «Ин.7:37-52,8:12», «Исх.12:51,13:1-3».

Текст — Синодальный перевод (data/bible/synodal.json, см. data/bible/README.md).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from src.cycle import DATA_DIR


@lru_cache(maxsize=1)
def load_bible() -> dict:
    with open(DATA_DIR / "bible" / "synodal.json", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class Verse:
    chapter: int
    verse: int
    text: str            # может содержать курсив <i>…</i>

    @property
    def plain(self) -> str:
        return re.sub(r"</?i>", "", self.text)


class RefError(ValueError):
    pass


def parse_ref(ref: str) -> tuple[str, list[tuple[int, int, int, int]]]:
    """«Ин.13:31-18:1» → ("Ин", [(13, 31, 18, 1)]).

    Отрывки через запятую; глава переносится из предыдущего отрывка, если не
    указана заново («Мк.5:22-24,35-43» → 5:22–24 и 5:35–43).
    """
    book, sep, rest = ref.replace(" ", "").replace("–", "-").partition(".")
    if not sep or not rest:
        raise RefError(f"не разобрать ссылку: {ref}")
    spans = []
    chapter = None
    for seg in rest.split(","):
        start, _, end = seg.partition("-")
        if ":" in start:
            c, v = start.split(":")
            chapter = int(c)
            v1 = int(v)
        elif chapter is not None:
            v1 = int(start)
        else:
            raise RefError(f"нет главы в ссылке: {ref}")
        c1 = chapter
        if not end:
            c2, v2 = c1, v1
        elif ":" in end:
            c, v = end.split(":")
            c2, v2 = int(c), int(v)
            chapter = c2
        else:
            c2, v2 = c1, int(end)
        spans.append((c1, v1, c2, v2))
    return book, spans


def passage(ref: str) -> list[Verse]:
    """Все стихи по ссылке. RefError, если книги, главы или стиха нет в тексте."""
    book, spans = parse_ref(ref)
    bible = load_bible()
    if book not in bible:
        raise RefError(f"нет книги «{book}» в тексте ({ref})")
    chapters = bible[book]
    out: list[Verse] = []
    for c1, v1, c2, v2 in spans:
        if c2 < c1 or (c2 == c1 and v2 < v1):
            raise RefError(f"обратный диапазон в ссылке: {ref}")
        for ch in range(c1, c2 + 1):
            verses = chapters.get(str(ch))
            if not verses:
                raise RefError(f"нет главы {book}.{ch} ({ref})")
            last = max(int(v) for v in verses)
            lo = v1 if ch == c1 else 1
            hi = v2 if ch == c2 else last
            for v in range(lo, hi + 1):
                text = verses.get(str(v))
                if text is None:
                    raise RefError(f"нет стиха {book}.{ch}:{v} ({ref})")
                out.append(Verse(ch, v, text))
    return out


def passage_text(ref: str) -> str:
    """Текст чтения одной строкой с номерами стихов (для CLI)."""
    parts = []
    prev_ch = None
    for v in passage(ref):
        num = f"{v.chapter}:{v.verse}" if v.chapter != prev_ch else str(v.verse)
        parts.append(f"[{num}] {v.plain}")
        prev_ch = v.chapter
    return " ".join(parts)
