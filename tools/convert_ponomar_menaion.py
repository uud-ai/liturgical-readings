#!/usr/bin/env python3
"""Минея: чтения святым на каждый день из проекта Ponomar → data/menaion.json.

Источник: https://github.com/typiconman/ponomar (GPL-3.0), русская практика:
  Ponomar/languages/cu/xml/MM/DD.xml       — какие памяти в этот день (ст. ст.)
  Ponomar/languages/xml/lives/<CId>.xml    — чтения памяти (утреня, литургия)
  Ponomar/languages/cu/xml/lives/<CId>.xml — знак службы (SERVICE Type)
  Ponomar/languages/cu/ru/xml/lives/<CId>.xml — имя по-русски

Использование:
    python tools/convert_ponomar_menaion.py <папка Ponomar/languages> data/menaion.json

Берутся только памяти с литургийными чтениями. Праздники (знак 6–8), дни,
уже описанные в data/feasts.json (праздники, навечерия, памяти с теми же
чтениями), и чтения с условиями, которые приложение не вычисляет, — пропускаются.
Паремии вечерни и чтения часов не переносятся.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bible_text import RefError, passage

BOOKS = {
    "Lk": "Лк", "Mk": "Мк", "Mt": "Мф", "Jn": "Ин", "Acts": "Деян", "Heb": "Евр",
    "Gal": "Гал", "Eph": "Еф", "II Cor": "2Кор", "I Cor": "1Кор", "Col": "Кол",
    "Philip": "Флп", "Jas": "Иак", "Rom": "Рим", "I Tim": "1Тим", "II Tim": "2Тим",
    "I Pet": "1Пет", "II Pet": "2Пет", "I Thess": "1Фес", "II Thess": "2Фес",
    "I Jn": "1Ин", "II Jn": "2Ин", "III Jn": "3Ин", "Jude": "Иуд", "Tit": "Тит",
    "Philemon": "Флм", "Isa": "Ис", "Gen": "Быт", "Prov": "Притч", "Wisd": "Прем",
    "Ex": "Исх", "Deut": "Втор", "Ezek": "Иез", "III Kings": "3Цар", "IV Kings": "4Цар",
    "Zech": "Зах", "Job": "Иов", "Jerem": "Иер", "Josh": "Нав", "Joel": "Иоил",
    "Mica": "Мих", "Mal": "Мал", "Judg": "Суд", "Zeph": "Соф", "Dan": "Дан",
    "Num": "Чис", "Baruch": "Вар", "Jona": "Иона", "Lev": "Лев",
}

# Знак службы Ponomar → ранг приложения. Бдение из автоматических данных не
# заменяет рядовые (это делают только проверенные записи data/feasts.json).
RANKS = {"5": "polyeleos", "4": "polyeleos", "0": "polyeleos"}

# Полиелей местночтимым святым на azbyka.ru — с пометкой «если совершается служба»
# (сверено: свт. Алексий 25.02.2025, прпп. Зосима и Савватий 21.08.2026);
# апостолам — без пометки (ап. Матфей 29.11.2025, ап. Марк 08.05.2025).
LOCAL = r"Московск|Черниговск|Соловецк|Почаевск|в Москве|Хутынск"

VESTMENT_PREFIXES = [
    (("Мч", "Мц", "Вмч", "Вмц", "Сщмч", "Прмч", "Прмц", "Свщмч", "Страстот"), "red"),
    (("Прп", "Блж", "Преп"), "green"),
    (("Икон", "иконы"), "blue"),
]


def convert_ref(reading: str) -> str | None:
    book, _, rest = reading.partition("_")
    code = BOOKS.get(book.strip())
    if not code or not rest:
        return None
    rest = re.sub(r"(\d)[a-c]\b", r"\1", rest.replace(" ", ""))
    ref = f"{code}.{rest}"
    try:
        passage(ref)
    except (RefError, ValueError):
        return None
    return ref


def zachalo(p: str) -> str | int:
    p = p.replace("(mid.)", "от полу").strip()
    return int(p) if p.isdigit() else p


def condition_ok(cmd: str) -> bool | None:
    """Простые условия: день недели (dow: 0 — воскресенье) и ранг дня.

    True/False — вычислено «для будня»; None — условие не поддерживается."""
    cmd = cmd.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    if re.fullmatch(r"dRank\s*[<!]=?\s*\d+", cmd):
        return True
    if re.fullmatch(r"dow\s*!=\s*0", cmd):
        return "weekday"
    return None


def read_xml(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    root = Path(__file__).resolve().parent.parent
    feasts = json.loads((root / "data" / "feasts.json").read_text(encoding="utf-8"))
    skip_days = set(feasts["feasts"]) | set(feasts["eves"])
    curated: dict[str, list[set]] = {}
    for c in feasts["commemorations"]:
        if c["rule"]["type"] == "fixed":
            refs = {r["ref"] for r in c["readings"] if r["service"] == "Литургия" and r.get("ref")}
            curated.setdefault(c["rule"]["date"], []).append(refs)

    menaion: dict[str, list] = {}
    for day_file in sorted(src.glob("cu/xml/[01][0-9]/[0-3][0-9].xml")):
        key = f"{day_file.parent.name}-{day_file.stem}"
        if key in skip_days:
            continue
        seen: list[set] = list(curated.get(key, []))
        for tag in re.findall(r"<SAINT ([^>]*)/>", read_xml(day_file)):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', tag))
            cid, cmd = attrs.get("CId", ""), attrs.get("Cmd", "")
            # Памяти с условием (переносы, подвижные дни) пропускаются; «nday != N»
            # значит «обычно — да, кроме особого подвижного дня».
            if cmd and not re.fullmatch(r"nday\s*!=\s*-?\d+", cmd):
                continue
            data = read_xml(src / "xml" / "lives" / f"{cid}.xml")
            if not data or "<LITURGY>" not in data:
                continue
            m = re.search(r'<SERVICE Type="(-?\d+)"', read_xml(src / "cu" / "xml" / "lives" / f"{cid}.xml"))
            sign = m.group(1) if m else ""
            if sign in ("6", "7", "8"):
                continue
            ru = read_xml(src / "cu" / "ru" / "xml" / "lives" / f"{cid}.xml")
            m = re.search(r'Nominative="([^"]+)"', ru)
            if not m:
                continue
            name = re.sub(r"\s*\([^)]*\)\.?", "", m.group(1)).strip().rstrip(".")
            name = name.replace("Translation of the relics of Вмч.", "Перенесение мощей вмч.")
            if re.search(r"[A-Za-z]", name):
                continue
            if re.search(r"вселенск|новомученик|РПЦЗ", name, re.IGNORECASE):
                continue                    # подвижные памяти — в data/feasts.json
            g = re.search(r'Genetive="([^"]+)"', ru)
            short = re.sub(r"\s*\([^)]*\)?", "", g.group(1) if g else name).strip().rstrip(".")
            if len(short.split()) < 2:
                short = name
            if not re.match(r"\w+\.|апостол|равноап|пророк|свят|мучени|преподоб|блажен", short, re.IGNORECASE):
                short = name                # «перенесение мощей» и т. п. — нужно полное имя
            short = short[0].lower() + short[1:]

            readings, ok = [], True
            for block, service in (("MATINS", "Утреня"), ("LITURGY", "Литургия")):
                b = re.search(rf"<{block}>(.*?)</{block}>", data, re.DOTALL)
                if not b:
                    continue
                for s in re.finditer(r"<SCRIPTURE ([^>]*)/>", b.group(1)):
                    attrs = dict(re.findall(r'(\w+)="([^"]*)"', s.group(1)))
                    cond = condition_ok(attrs["Cmd"]) if "Cmd" in attrs else True
                    if cond is None:
                        ok = False
                        break
                    ref = convert_ref(attrs.get("Reading", ""))
                    if not ref:
                        ok = False
                        break
                    kind = attrs.get("Type", "")
                    label = ("Евангелие" if service == "Утреня" or kind == "gospel"
                             else "Апостол" if kind == "apostol" else None)
                    if not label:
                        ok = False
                        break
                    r = {"service": service, "label": label, "ref": ref}
                    if attrs.get("Pericope"):
                        r["zachalo"] = zachalo(attrs["Pericope"])
                    if cond == "weekday":
                        r["weekday_only"] = True
                    readings.append(r)
                if not ok:
                    break
            lit = {r["ref"] for r in readings if r["service"] == "Литургия"}
            if not ok or not lit or any(lit & s for s in seen):
                continue
            seen.append(lit)
            rank = RANKS.get(sign, "lesser")
            entry = {"name": name, "short": short, "rank": rank, "sign": sign,
                     "readings": readings}
            for prefixes, color in VESTMENT_PREFIXES:
                if name.startswith(prefixes):
                    entry["vestment"] = color
                    break
            if sign == "0" or (sign == "4" and re.search(LOCAL, name)):
                entry["conditional"] = True     # местночтимые: «если совершается служба»
            menaion.setdefault(key, []).append(entry)

    out.write_text(json.dumps({
        "_comment": ("Минея: чтения святым по дням (ключ — дата ст. ст.). Источник — проект "
                     "Ponomar (русская практика, GPL-3.0), конвертер tools/convert_ponomar_menaion.py. "
                     "sign — знак службы по Ponomar (5 — бдение, 4 — полиелей, 3–1 — "
                     "славословие/шестеричная, 0 — местное празднование; местночтимым — с пометкой "
                     "«если совершается служба»). Проверенные записи "
                     "data/feasts.json главнее: совпадающие памяти отсюда исключены."),
        **menaion}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(v) for v in menaion.values())
    print(f"{len(menaion)} дней, {n} памятей → {out}")


if __name__ == "__main__":
    main()
