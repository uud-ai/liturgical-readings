"""Получение чтений дня (Евангелие и Апостол по зачалам)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache

from src.cycle import DATA_DIR, DayPosition, Slot, eothinon, resolve
from src.links import bible_url, day_url


@lru_cache(maxsize=1)
def load_ordinary_cycle() -> dict:
    with open(DATA_DIR / "ordinary_cycle.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_feasts() -> dict:
    with open(DATA_DIR / "feasts.json", encoding="utf-8") as f:
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


def _week_label(slot: Slot | None) -> str:
    if slot is None:
        return "этого дня (по особому правилу)"
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
    kind: str          # apostle | gospel | matins | vespers | triodion | feast
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
        label = (f"{self.service}. {self.label}" if self.kind in ("triodion", "feast")
                 else self.label)
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
        self.unresolved = bool(pos.unresolved)
        if pos.triodion_day:
            entry = load_triodion()[str(pos.triodion_day)]
            self.title, self.note = entry["title"], ""
            self.items = self._triodion_items(entry)
            if entry.get("note"):
                self.notes.insert(0, entry["note"])
        else:
            self.title, self.note = self._title_and_note()
            self.items = [] if pos.unresolved else self._items()
        self.feast_kind = ""
        self._apply_fixed_feasts()

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
            if slot is None:
                items.append(Item(kind, label, service="Литургия",
                                  missing="рядовое — из Матфеевых седмиц, смотрите богослужебные указания."))
            elif ref:
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

    # --- неподвижные двунадесятые праздники и навечерия -----------------

    def _apply_fixed_feasts(self) -> None:
        data = load_feasts()
        old = self.day - timedelta(days=13)          # старый стиль (1900–2099)
        key = f"{old.month:02d}-{old.day:02d}"
        wd = self.day.weekday()                       # 0 — понедельник, 6 — воскресенье

        # Царские часы, перенесённые на пятницу, если навечерие — в субботу/воскресенье.
        if wd == 4:
            for delta in (1, 2):
                o = old + timedelta(days=delta)
                eve = data["eves"].get(f"{o.month:02d}-{o.day:02d}")
                if eve:
                    self._replace(eve["title"].split(" (")[0] + ": Царские часы",
                                  eve["royal_hours"],
                                  ["Царские часы перенесены на пятницу, так как навечерие "
                                   "приходится на " + ("субботу." if delta == 1 else "воскресенье."),
                                   "Литургия в этот день не совершается."])
                    return

        if key in data["eves"]:
            eve = data["eves"][key]
            if wd <= 4:
                self._replace(eve["title"], eve["weekday"],
                              ["Рядовые чтения в этот день не читаются."])
            else:
                friday = self.day - timedelta(days=wd - 4)
                items = list(eve["saturday" if wd == 5 else "sunday"]) + eve["weekend_vespers"]
                notes = [f"Царские часы перенесены на пятницу, {friday.strftime('%d.%m')}."]
                if wd == 5:
                    notes.append(eve["saturday_note"])
                self._replace(eve["title"], items, notes, keep_eothinon=(wd == 6))
            return

        feast = data["feasts"].get(key)
        special = next((sp for sp in data["special_days"]
                        if sp["weekday"] == wd and sp["from"] <= key <= sp["to"]), None)
        if special:
            self._special_day(special, feast)
            return
        if not feast:
            for c in data.get("commemorations", []):
                if self._commemoration_matches(c, key, wd):
                    self._apply_commemoration(c)
            return
        self.feast_kind = feast["kind"]
        base_title = "" if self.unresolved else (self.pos.title or self.title)
        if feast["kind"] == "lord":
            notes = ["Господский двунадесятый праздник: " + (
                "воскресные и рядовые чтения" if wd == 6 else "рядовые чтения") +
                " в этот день не читаются."]
            if key == "02-02" and self.pos.triodion_day == 48:
                notes.append("Сретение в Чистый понедельник по уставу переносится на "
                             "Неделю сыропустную — смотрите богослужебные указания.")
            if self.pos.triodion_day and wd == 6:
                # Недели Триоди не уступают празднику: на литургии — Недели и праздника.
                self._feast_with_sunday(feast, base_title, "праздника", [
                    "Господский праздник в Неделю Триоди: утреннее Евангелие — праздника; "
                    "на литургии читаются чтения Недели и праздника."])
                return
            if self.pos.triodion_day:
                notes.append("Праздник в будний день Триоди: возможно чтение дня под зачало — "
                             "сверьте с богослужебными указаниями.")
            self._replace(feast["title"], feast["readings"], notes, subtitle=base_title)
        elif feast["kind"] == "great" and wd == 6:
            # Великий праздник в воскресенье: утреня — воскресная, литургия — Недели и праздника.
            self._feast_with_sunday(feast, base_title, "праздника", [
                "Великий праздник в воскресенье: утреннее Евангелие — воскресное; "
                "на литургии читаются чтения Недели и праздника."], sunday_matins=True)
            if feast.get("note"):
                self.notes.append(feast["note"])
        elif feast["kind"] in ("theotokos", "great"):
            if wd < 6:
                self._replace(feast["title"], feast["readings"],
                              ["Рядовые чтения в этот день не читаются."]
                              + ([feast["note"]] if feast.get("note") else []),
                              subtitle=base_title)
            else:
                self._theotokos_sunday(feast, base_title)
        else:
            self._annunciation(feast, base_title)

    def _special_day(self, sp: dict, feast: dict | None) -> None:
        """Особые субботы и Недели пред и по Рождестве и Богоявлении, Неделя праотец."""
        base_title = "" if self.unresolved else (self.pos.title or self.title)
        matins = []
        if self.day.weekday() == 6 and self.pos.sunday_after_pentecost:
            n, ref, z = eothinon(self.pos.sunday_after_pentecost)
            matins = [Item("feast", f"Евангелие {n}-е воскресное", ref, str(z), service="Утреня")]
        items = matins + self._feast_items(sp["readings"])
        notes = []
        if sp["ordinary"] == "omit":
            notes.append("Рядовые чтения в эту Неделю не читаются.")
        else:
            ordinary = [] if self.unresolved else [
                i for i in self.items if i.service == "Литургия" and (i.ref or i.parts)]
            if ordinary:
                items += [Item("feast", "Апостол рядовой (под зачало)" if i.kind == "apostle"
                               else "Евангелие рядовое (под зачало)", i.ref, i.zachalo,
                               service="Литургия") for i in ordinary]
                notes += [n for n in self.notes if n.startswith(("Евангелие —", "Апостол —"))]
            else:
                notes.append("Читаются также рядовые чтения (под зачало) — в этот период "
                             "смотрите богослужебные указания.")
        title, subtitle = sp["name"], base_title
        if feast:
            self.feast_kind = feast["kind"]
            f = self._feast_items(feast["readings"])
            suffix = "Богородицы" if feast["kind"] == "theotokos" else "праздника"
            eve = [i for i in f if i.service.startswith("Вечерня")]
            f_matins = [i for i in f if i.service == "Утреня"]
            f_lit = [Item("feast", f"{i.label} {suffix}" if i.label in ("Апостол", "Евангелие")
                          else i.label, i.ref, i.zachalo, service=i.service, parts=i.parts)
                     for i in f if i.service not in ("Утреня",) and not i.service.startswith("Вечерня")]
            if feast["kind"] == "theotokos":
                matins = f_matins           # Богородичный: утреннее Евангелие праздника
            body = [i for i in items if i.service != "Утреня"]
            items = eve + matins + body + f_lit
            title, subtitle = feast["title"], sp["name"]
            notes.insert(0, "Праздник совпадает с особым днём: читаются чтения особого дня "
                            "и праздника.")
        self.title, self.note = title, subtitle
        self.items = items
        self.notes = notes
        self.unresolved = False

    # --- памяти святых и икон, памятные воскресенья -----------------------

    def _commemoration_matches(self, c: dict, key: str, wd: int) -> bool:
        rule = c["rule"]
        if rule["type"] == "fixed":
            return key == rule["date"]
        if rule["type"] == "sunday_range":
            return wd == 6 and rule["from"] <= key <= rule["to"]
        if rule["type"] == "pentecost_sunday":
            return (wd == 6 and not self.pos.triodion_day and self.pos.apostle is not None
                    and self.pos.apostle.period == "pentecost_period"
                    and self.pos.sunday_after_pentecost == rule["n"])
        if rule["type"] == "bright_friday":
            return self.pos.apostle == Slot("pascha_period", "2", "fri")
        if rule["type"] == "new_martyrs":
            # 25 января ст. ст. (7 февраля); пн–ср — предыдущее воскресенье,
            # чт–сб — следующее (Архиерейский Собор 2013 г.).
            f = date(self.day.year, 2, 7)
            w = f.weekday()
            if w == 6:
                target = f
            elif w <= 2:
                target = f - timedelta(days=w + 1)
            else:
                target = f + timedelta(days=6 - w)
            return self.day == target
        return False

    def _apply_commemoration(self, c: dict) -> None:
        name, suffix, rank = c["name"], c["suffix"], c["rank"]
        wd = self.day.weekday()
        n = self.pos.triodion_day
        a = self.pos.apostle
        bright = a is not None and a.period == "pascha_period" and a.week in ("pascha", "2")
        special_day = (bool(n and n <= 6) or (bright and c["rule"]["type"] != "bright_friday")
                       or a in (Slot("pascha_period", "7", "thu"),
                                Slot("pascha_period", "pentecost", "sun")))
        if special_day:
            self.notes.append(f"Память: {name}. В этот день служба совершается по особому "
                              f"уставу — смотрите богослужебные указания.")
            return
        f = self._feast_items(c["readings"])
        eve = [i for i in f if i.service.startswith("Вечерня (накануне)")]
        matins = [i for i in f if i.service == "Утреня"]
        lit = [Item("feast", f"{i.label} {suffix}", i.ref, i.zachalo, service="Литургия",
                    parts=i.parts) for i in f if i.service == "Литургия"]
        if n and 9 <= n <= 48 and wd <= 4:
            self.items = matins + self.items
            self.note = name
            self.notes.append(f"{name}: в будни Великого поста литургийных чтений памяти нет.")
            return
        base_title = "" if self.unresolved else (self.pos.title or self.title)
        in_pascha = a is not None and a.period == "pascha_period"
        if rank == "vigil" and wd <= 5 and not in_pascha:
            self._replace(name, c["readings"], ["Рядовые чтения в этот день не читаются."],
                          subtitle=base_title)
            self.feast_kind = "vigil"
            return
        base = [Item("feast", i.label, i.ref, i.zachalo, i.missing, i.service, i.parts)
                for i in self.items]
        base_matins = [i for i in base if i.service == "Утреня"]
        base_rest = [i for i in base if i.service != "Утреня"]
        if wd == 6:
            matins = base_matins            # в воскресенье утреннее Евангелие — воскресное
            if not matins and self.pos.sunday_after_pentecost:
                k, ref, z = eothinon(self.pos.sunday_after_pentecost)
                matins = [Item("feast", f"Евангелие {k}-е воскресное", ref, str(z),
                               service="Утреня")]
        elif bright:
            matins = []
        if rank == "sunday":
            eve = []
        self.items = eve + matins + base_rest + lit
        if self.unresolved:
            self.unresolved = False         # сообщение о рядовых остаётся в notes
        else:
            self.note = name if not self.note else f"{self.note}. {name}"
        if self.unresolved is False and not base_title:
            self.title = name
        self.feast_kind = self.feast_kind or rank
        self.notes.append("На литургии читаются чтения " + ("Недели" if wd == 6 else "дня")
                          + " и памяти.")

    @staticmethod
    def _feast_items(readings: list[dict]) -> list[Item]:
        return [Item("feast", r["label"], r.get("ref", ""), str(r.get("zachalo", "")),
                     service=r["service"],
                     parts=[Part(p["ref"], str(p.get("zachalo", ""))) for p in r.get("parts", [])])
                for r in readings]

    def _replace(self, title, readings, notes, subtitle="", keep_eothinon=False):
        eothinon_items = [i for i in self.items if i.service == "Утреня"] if keep_eothinon else []
        if keep_eothinon and not eothinon_items and self.pos.sunday_after_pentecost:
            n, ref, z = eothinon(self.pos.sunday_after_pentecost)
            eothinon_items = [Item("feast", f"Евангелие {n}-е воскресное", ref, str(z),
                                   service="Утреня")]
        self.title, self.note = title, subtitle
        self.items = eothinon_items + self._feast_items(readings)
        self.notes = notes
        self.unresolved = False

    def _theotokos_sunday(self, feast, base_title):
        self._feast_with_sunday(feast, base_title, "Богородицы", [
            "Богородичный праздник в воскресенье: утреннее Евангелие — праздника; "
            "на литургии читаются чтения Недели и праздника."])

    def _feast_with_sunday(self, feast, base_title, suffix, head_notes, sunday_matins=False):
        f = self._feast_items(feast["readings"])
        if sunday_matins:
            f = [i for i in f if i.service != "Утреня"]
            if self.pos.sunday_after_pentecost:
                n, ref, z = eothinon(self.pos.sunday_after_pentecost)
                pos = sum(1 for i in f if i.service.startswith("Вечерня (накануне)"))
                f.insert(pos, Item("feast", f"Евангелие {n}-е воскресное", ref, str(z),
                                   service="Утреня"))
        sunday_lit = [Item("feast", f"{i.label} Недели", i.ref, i.zachalo, service="Литургия",
                           parts=i.parts)
                      for i in self.items if i.service == "Литургия" and (i.ref or i.parts)]
        feast_lit = [Item("feast", f"{i.label} {suffix}", i.ref, i.zachalo,
                          service="Литургия") for i in f if i.service == "Литургия"]
        before = [i for i in f if i.service != "Литургия"]   # вечерня накануне, утреня праздника
        notes = list(head_notes)
        notes += [n for n in self.notes if not n.startswith(("Евангелие —", "Апостол —"))]
        self.title, self.note = feast["title"], base_title
        self.items = before + sunday_lit + feast_lit
        self.notes = notes
        self.unresolved = False

    def _annunciation(self, feast, base_title):
        f = self._feast_items(feast["readings"])
        n = self.pos.triodion_day
        wd = self.day.weekday()
        base = [i for i in self.items if wd == 6 or i.service != "Утреня"]
        feast_eve = [i for i in f if i.service.startswith("Вечерня")]
        feast_matins = [i for i in f if i.service == "Утреня"]
        feast_lit = [i for i in f if i.service == "Литургия"]
        base_lit = [i for i in base if i.service == "Литургия"]
        other = [i for i in base if i.service != "Литургия"]
        lenten_weekday = bool(n and 4 <= n <= 48 and wd <= 4)
        if lenten_weekday:
            other += [Item("feast", r["label"], r["ref"], service="Вечерня")
                      for r in feast["lenten_vespers"]]
        lit = (feast_lit + base_lit) if (n and n <= 6) else (base_lit + feast_lit)
        rank = {"Утреня": 1, "1-й час": 2, "3-й час": 3, "6-й час": 4, "9-й час": 5,
                "Вечерня": 6, "Литургия": 7}
        body = sorted(feast_matins + other + lit, key=lambda i: rank.get(i.service, 8))
        notes = ["Благовещение: чтения праздника читаются вместе с чтениями дня."]
        if wd == 6 and any(i.service == "Утреня" for i in base):
            notes.append("В воскресенье порядок утренних Евангелий при Благовещении — "
                         "смотрите богослужебные указания.")
        if lenten_weekday:
            notes.append("Совершается Литургия свт. Иоанна Златоуста с вечерней.")
        if (n and n <= 3) or self.pos.apostle and self.pos.apostle.period == "pascha_period" \
                and self.pos.apostle.week in ("pascha", "2"):
            notes.append("Совпадение Благовещения с последними днями Страстной седмицы или "
                         "Светлой седмицей имеет особый устав — смотрите богослужебные указания.")
        self.title, self.note = feast["title"], base_title
        self.items = feast_eve + body
        self.notes = notes
        self.unresolved = False

    def format(self) -> str:
        lines = [f"Чтения на {self.day.strftime('%d.%m.%Y')}"]
        if not self.unresolved:
            lines.append(self.title)
            if self.note:
                lines.append(self.note)
        # В тексте порядок привычный: Апостол, Евангелие, затем утреннее.
        order = {"apostle": 0, "gospel": 1, "matins": 2, "vespers": 3, "triodion": 4, "feast": 4}
        lines += [i.text() for i in sorted(self.items, key=lambda i: order[i.kind])]
        lines += self.notes
        return "\n".join(lines)


def get_reading(day: date) -> Reading:
    return Reading(day, resolve(day))
