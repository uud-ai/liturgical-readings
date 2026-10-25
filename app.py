import os
import re
from datetime import date, timedelta

from flask import Flask, request, send_from_directory
from markupsafe import Markup, escape

from src.bible_text import RefError, passage
from src.cycle import FIRST_DAY, LAST_DAY
from src.readings import get_reading

app = Flask(__name__)


def passage_html(ref: str):
    """Текст чтения в HTML: номера стихов, курсив Синодального перевода и
    киноварный инициал в начале чтения."""
    try:
        verses = passage(ref)
    except (RefError, ValueError):
        return None
    out, prev = [], None
    for k, v in enumerate(verses):
        num = f"{v.chapter}:{v.verse}" if v.chapter != prev else str(v.verse)
        text = str(escape(v.text)).replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        text = text.replace(" -- ", "\u00a0— ").replace("--", "—")
        sup = f"<sup>{num}</sup>"
        if k == 0:
            m = re.match(r"((?:<i>)?)([^\W\d_])", text)
            if m:
                initial = f'<span class="initial" aria-hidden="true">{m.group(2)}</span>'
                rest = f'<span class="sr-only">{m.group(2)}</span>'
                out.append(initial + sup + m.group(1) + rest + text[m.end():])
                prev = v.chapter
                continue
        out.append(sup + text)
        prev = v.chapter
    return Markup(" ".join(out))


def pretty_ref(ref: str) -> str:
    """«Ин.21:1-14» → «Ин. 21:1–14» (узкий пробел, короткое тире)."""
    book, sep, rest = ref.partition(".")
    if not sep:
        return ref
    return f"{book}.\u202f" + rest.replace("-", "\u2013").replace(",", ", ")


app.jinja_env.globals["passage_html"] = passage_html
app.jinja_env.filters["ref"] = pretty_ref

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница",
            "суббота", "воскресенье"]


def ru_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def old_style(d: date) -> str:
    """Дата по старому стилю (разница 13 дней в 1900–2099 гг.)."""
    o = d - timedelta(days=13)
    return f"{o.day}\u00a0{MONTHS[o.month - 1]}"


PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{% set v = r.vestment.key if r else "gold" %}
{% set band = {"gold": "#B98B34", "white": "#ECE6D9", "red": "#8E1D20", "blue": "#35638F",
               "green": "#355F3D", "purple": "#552951", "black": "#221E1C"}[v] %}
<meta name="theme-color" content="{{ band }}">
<title>{% if r %}{{ r.title }} — {% endif %}чтения на {{ date_short }}</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{% if not error %}<link rel="prefetch" href="?date={{ next }}"><link rel="prefetch" href="?date={{ prev }}">{% endif %}
<link href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=Old+Standard+TT:ital@0;1&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #FBFAF7; --ink: #211D19; --muted: #756D64; --hair: #E7E1D6;
    --rubric: #B3261E; --rubric-soft: #F6E7E3; --focus: #B3261E;
    --serif: "Old Standard TT", "Times New Roman", serif;
    --sans: "Golos Text", system-ui, sans-serif;
    --trim-a: #D8B45C; --trim-b: #9E7A2C;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #191714; --ink: #ECE5DA; --muted: #A39A8E; --hair: #332E28;
      --rubric: #E36A55; --rubric-soft: #2E1F1B; --focus: #E36A55;
    }
  }
  /* Цвет облачения дня */
  .v-gold   { --v: #C49638; --v-deep: #8E6520; --on: #2A1C05; --on-soft: rgba(42,28,5,.72);
              --orn: rgba(255,236,186,.30); --chip: rgba(42,28,5,.08); --chip-line: rgba(42,28,5,.3);
              --trim-a: #F0D68E; --trim-b: #7A5717; --scheme: light; }
  .v-white  { --v: #F0EBDF; --v-deep: #D8CDB5; --on: #2B241B; --on-soft: rgba(43,36,27,.7);
              --orn: rgba(176,140,62,.30); --chip: rgba(43,36,27,.06); --chip-line: rgba(43,36,27,.26);
              --scheme: light; }
  .v-red    { --v: #9C2124; --v-deep: #651316; --on: #FFF3EA; --on-soft: rgba(255,243,234,.8);
              --orn: rgba(238,198,118,.24); --chip: rgba(255,255,255,.1); --chip-line: rgba(255,243,234,.4);
              --scheme: dark; }
  .v-blue   { --v: #3D6E9E; --v-deep: #24486D; --on: #F4F8FC; --on-soft: rgba(244,248,252,.8);
              --orn: rgba(255,255,255,.16); --chip: rgba(255,255,255,.1); --chip-line: rgba(244,248,252,.42);
              --trim-a: #E3E6EA; --trim-b: #8D97A3; --scheme: dark; }
  .v-green  { --v: #3B6A44; --v-deep: #213F27; --on: #F1F6EE; --on-soft: rgba(241,246,238,.8);
              --orn: rgba(236,206,132,.2); --chip: rgba(255,255,255,.1); --chip-line: rgba(241,246,238,.4);
              --scheme: dark; }
  .v-purple { --v: #602E5B; --v-deep: #381735; --on: #FAEFF8; --on-soft: rgba(250,239,248,.8);
              --orn: rgba(236,206,132,.2); --chip: rgba(255,255,255,.1); --chip-line: rgba(250,239,248,.4);
              --scheme: dark; }
  .v-black  { --v: #2A2523; --v-deep: #131110; --on: #EFE9E1; --on-soft: rgba(239,233,225,.76);
              --orn: rgba(214,214,220,.14); --chip: rgba(255,255,255,.08); --chip-line: rgba(239,233,225,.34);
              --trim-a: #D4D6DA; --trim-b: #6E7279; --scheme: dark; }

  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body { margin: 0; background: var(--paper); color: var(--ink);
         font: 16px/1.55 var(--sans); }
  a { color: inherit; }
  :focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; border-radius: 4px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
             clip: rect(0 0 0 0); white-space: nowrap; }
  .wrap { max-width: 680px; margin: 0 auto; padding: 0 20px; }

  /* Облачение: ткань с узором и галун по краю */
  .vestment { position: relative; color: var(--on); color-scheme: var(--scheme);
              background: linear-gradient(165deg, var(--v) 0%, var(--v-deep) 100%);
              padding: max(16px, env(safe-area-inset-top)) 0 0; isolation: isolate; }
  .vestment::before { content: ""; position: absolute; inset: 0; z-index: -1;
    background: var(--orn);
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='44' height='44' viewBox='0 0 44 44'%3E%3Cg fill='none' stroke='%23000'%3E%3Cpath d='M0 22L22 0L44 22L22 44Z' stroke-width='.7'/%3E%3Cpath d='M22 13v18M13 22h18' stroke-width='2.2'/%3E%3Cpath d='M19 13h6M19 31h6M13 19v6M31 19v6' stroke-width='1.2'/%3E%3C/g%3E%3Cg%3E%3Ccircle cx='0' cy='0' r='1.6'/%3E%3Ccircle cx='44' cy='0' r='1.6'/%3E%3Ccircle cx='0' cy='44' r='1.6'/%3E%3Ccircle cx='44' cy='44' r='1.6'/%3E%3C/g%3E%3C/svg%3E") 0 0 / 44px 44px repeat;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='44' height='44' viewBox='0 0 44 44'%3E%3Cg fill='none' stroke='%23000'%3E%3Cpath d='M0 22L22 0L44 22L22 44Z' stroke-width='.7'/%3E%3Cpath d='M22 13v18M13 22h18' stroke-width='2.2'/%3E%3Cpath d='M19 13h6M19 31h6M13 19v6M31 19v6' stroke-width='1.2'/%3E%3C/g%3E%3Cg%3E%3Ccircle cx='0' cy='0' r='1.6'/%3E%3Ccircle cx='44' cy='0' r='1.6'/%3E%3Ccircle cx='0' cy='44' r='1.6'/%3E%3Ccircle cx='44' cy='44' r='1.6'/%3E%3C/g%3E%3C/svg%3E") 0 0 / 44px 44px repeat; }
  .vestment::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 12px;
    background:
      linear-gradient(var(--trim-b), var(--trim-b)) top / 100% 1px no-repeat,
      linear-gradient(var(--trim-b), var(--trim-b)) bottom / 100% 1px no-repeat,
      repeating-linear-gradient(135deg, var(--trim-a) 0 4px, var(--trim-b) 4px 5px, var(--trim-a) 5px 9px); }

  nav { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  nav a, nav button, nav input {
    font: 500 14px/1 var(--sans); color: var(--on); background: var(--chip);
    border: 1px solid var(--chip-line); border-radius: 999px; padding: 9px 14px;
    text-decoration: none; cursor: pointer; min-height: 38px;
    display: inline-flex; align-items: center; justify-content: center; }
  nav a:hover, nav button:hover { background: var(--chip-line); }
  nav a[aria-current] { background: var(--on); color: var(--v-deep); border-color: var(--on); }
  nav .step { width: 38px; padding: 0; font-size: 17px; }
  nav form { display: flex; gap: 6px; margin-left: auto; }
  nav input { cursor: text; padding: 8px 12px; font-variant-numeric: tabular-nums; }

  header.day { padding: 44px 0 52px; }
  .when { margin: 0; font-size: 15px; font-weight: 500; letter-spacing: .01em; }
  .when span { display: block; font-weight: 400; color: var(--on-soft); margin-top: 2px; }
  h1 { font: 400 clamp(32px, 6.2vw, 46px)/1.12 var(--serif); margin: 22px 0 0;
       letter-spacing: -.005em; text-wrap: balance; }
  .subtitle { font: italic 19px/1.4 var(--serif); margin: 12px 0 0; color: var(--on-soft);
              text-wrap: pretty; }
  .robe { margin: 26px 0 0; font-size: 14px; color: var(--on-soft); display: flex;
          align-items: center; gap: 9px; }
  .robe::before { content: ""; width: 9px; height: 9px; transform: rotate(45deg);
                  background: var(--trim-a); box-shadow: 0 0 0 1px var(--trim-b); }

  main { padding: 26px 0 64px; }
  .tools { display: flex; justify-content: flex-end; margin: 4px 0 2px; }
  .toggle-all { font: 500 14px var(--sans); color: var(--rubric); background: none;
                border: 0; padding: 6px 0; cursor: pointer; }
  .toggle-all:hover { text-decoration: underline; text-underline-offset: 3px; }

  .service { margin-top: 28px; }
  .service:first-of-type { margin-top: 8px; }
  .service h2 { font: italic 400 22px/1.2 var(--serif); color: var(--rubric); margin: 0;
                display: flex; align-items: center; gap: 14px; }
  .service h2::after { content: ""; flex: 1; height: 1px; background: var(--hair); }

  .reading { border-bottom: 1px solid var(--hair); }
  .reading:last-child { border-bottom: 0; }
  .reading > summary, .part > summary { list-style: none; cursor: pointer;
    display: grid; grid-template-columns: 1fr auto; column-gap: 16px; align-items: end;
    padding: 16px 0 15px; }
  summary::-webkit-details-marker { display: none; }
  .label { grid-column: 1 / -1; font-size: 14px; color: var(--muted); margin-bottom: 3px; }
  .ref { font: 400 27px/1.2 var(--serif); font-variant-numeric: lining-nums; }
  .meta { display: flex; align-items: center; gap: 12px; color: var(--muted);
          font-size: 13px; white-space: nowrap; padding-bottom: 4px; }
  .chev { width: 26px; height: 26px; border-radius: 50%; border: 1px solid var(--hair);
          display: inline-grid; place-items: center; color: var(--rubric); font-size: 14px;
          transition: transform .2s ease, background .2s ease; }
  details[open] > summary .chev { transform: rotate(90deg); background: var(--rubric-soft); }
  summary:hover .ref { color: var(--rubric); }
  .group-label { font-size: 14px; color: var(--muted); padding-top: 16px; }
  .part > summary { padding: 6px 0 8px; }
  .part .ref { font-size: 23px; }
  .parts { padding-bottom: 10px; border-bottom: 1px solid var(--hair); }
  .missing { padding: 16px 0; border-bottom: 1px solid var(--hair); }
  .missing p { margin: 2px 0 0; font: italic 17px/1.45 var(--serif); color: var(--muted); }

  .text { font: 400 19px/1.78 var(--serif); margin: 2px 0 22px; hyphens: auto;
          text-wrap: pretty; max-width: 62ch; }
  .text sup { font: 600 10.5px var(--sans); color: var(--rubric); margin: 0 3px 0 5px;
              vertical-align: .55em; line-height: 0; }
  .initial { float: left; font: 400 3.95em/0.82 var(--serif); color: var(--rubric);
             text-transform: uppercase;
             margin: 0.08em 0.1em 0 0; padding-top: 0.04em; }
  .text .initial + sup { margin-left: 0; }

  .unresolved { font: italic 18px/1.5 var(--serif); color: var(--muted); margin: 18px 0; }

  .rubrics { margin: 34px 0 0; padding: 18px 0 0; border-top: 1px solid var(--hair); }
  .rubrics p { font: italic 16px/1.55 var(--serif); color: var(--rubric); margin: 0 0 10px;
               text-wrap: pretty; }

  footer { margin-top: 42px; font-size: 13px; line-height: 1.6; color: var(--muted); max-width: 60ch; }

  @media (max-width: 520px) {
    .wrap { padding: 0 16px; }
    nav form { margin-left: 0; width: 100%; }
    nav input { flex: 1; }
    header.day { padding: 34px 0 44px; }
    .ref { font-size: 24px; }
    .text { font-size: 18px; }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
  @media print {
    .vestment { background: none; color: #000; }
    .vestment::before, .vestment::after, nav, .tools { display: none; }
    details > *:not(summary) { display: block; }
  }
</style>
</head>
<body class="v-{{ v }}">
<div class="vestment">
  <div class="wrap">
    <nav aria-label="Выбор дня">
      <a class="step" href="?date={{ prev }}" aria-label="Предыдущий день">‹</a>
      <a href="/" id="today">Сегодня</a>
      <a class="step" href="?date={{ next }}" aria-label="Следующий день">›</a>
      <form method="get">
        <input type="date" name="date" value="{{ iso }}" min="1900-03-14" max="2099-12-31" required aria-label="Дата">
        <button type="submit">Открыть</button>
      </form>
    </nav>
    <header class="day">
      {% if error %}
        <h1>Не удалось открыть этот день</h1>
        <p class="subtitle">{{ error }}</p>
      {% else %}
        <p class="when">{{ weekday }}, {{ date_long }}<span>{{ old }} по старому стилю</span></p>
        <h1>{{ r.title }}</h1>
        {% if r.note %}<p class="subtitle">{{ r.note }}</p>{% endif %}
        <p class="robe">Облачение {{ r.vestment.name }}</p>
      {% endif %}
    </header>
  </div>
</div>

<main class="wrap">
{% if not error %}
  {% macro body(ref) %}
    {% set t = passage_html(ref) %}
    {% if t %}<div class="text">{{ t }}</div>{% endif %}
  {% endmacro %}
  {% macro summary(label, ref, zachalo) %}
    <summary>
      {% if label %}<span class="label">{{ label }}</span>{% endif %}
      <span class="ref">{{ ref|ref }}</span>
      <span class="meta">{% if zachalo %}зач. {{ zachalo }}{% endif %}<span class="chev" aria-hidden="true">›</span></span>
    </summary>
  {% endmacro %}

  {% if r.items %}
  <div class="tools"><button class="toggle-all" type="button" onclick="
    var d=document.querySelectorAll('main details'), open=![].every.call(d,function(x){return x.open});
    d.forEach(function(x){x.open=open}); this.textContent=open?'Свернуть все тексты':'Раскрыть все тексты';">Раскрыть все тексты</button></div>
  {% endif %}

  {% for service, items in r.groups %}
    <section class="service">
      {% if service %}<h2>{{ service }}</h2>{% endif %}
      {% for i in items %}
        {% if i.parts %}
          <div class="parts">
            <div class="group-label">{{ i.label }}</div>
            {% for p in i.parts %}
              <details class="part">{{ summary("", p.ref, p.zachalo) }}{{ body(p.ref) }}</details>
            {% endfor %}
          </div>
        {% elif i.ref %}
          <details class="reading">{{ summary(i.label, i.ref, i.zachalo) }}{{ body(i.ref) }}</details>
        {% else %}
          <div class="missing"><span class="label">{{ i.label }}</span><p>{{ i.missing }}</p></div>
        {% endif %}
      {% endfor %}
    </section>
  {% else %}
    <p class="unresolved">Рядовые чтения на этот день приложение пока не выдаёт — смотрите богослужебные указания.</p>
  {% endfor %}

  {% if r.notes %}
  <section class="rubrics" aria-label="Указания">
    {% for n in r.notes|unique %}<p>{{ n }}</p>{% endfor %}
  </section>
  {% endif %}

  <footer>
    Рядовые чтения, Триодь постная, праздники и чтимые святые по уставу Русской Церкви.
    Текст — Синодальный перевод. Цвет облачения указан по общему обычаю, местная практика
    может отличаться.
  </footer>
{% endif %}
</main>
<script>
  // «Сегодня» — по часам читателя, без лишнего перехода через «/».
  (function () {
    var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
    var iso = d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
    var a = document.getElementById("today");
    a.href = "?date=" + iso;
    if (iso === "{{ iso }}") a.setAttribute("aria-current", "date");
  })();
</script>
</body>
</html>
"""

# Сервер (Vercel) работает в UTC, а «сегодня» у читателя — по его часовому
# поясу. Если дата не передана, страница сама подставляет локальную дату.
LOCAL_DATE_REDIRECT = """<!doctype html><meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<style>body{background:#FBFAF7}@media(prefers-color-scheme:dark){body{background:#191714}}</style>
<script>
var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
location.replace("?date=" + d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()));
</script>
<noscript><meta http-equiv="refresh" content="0; url=?date={today}"></noscript>
"""


PAGE_TEMPLATE = app.jinja_env.from_string(PAGE)   # компилируется один раз

# Страница дня зависит только от даты и версии кода: браузер держит её 5 минут,
# CDN Vercel — сутки (новый деплой сбрасывает кэш CDN).
CACHE_DAY = "public, max-age=300, s-maxage=86400, stale-while-revalidate=604800"
CACHE_SHORT = "public, max-age=0, s-maxage=600"

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
PUBLIC_FILES = ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png",
                "icon-512.png", "site.webmanifest")


def page(status: int = 200, cache: str = CACHE_DAY, **ctx):
    return PAGE_TEMPLATE.render(**ctx), status, {
        "Content-Type": "text/html; charset=utf-8", "Cache-Control": cache}


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\n", 200, {
        "Content-Type": "text/plain; charset=utf-8", "Cache-Control": CACHE_DAY}


# На Vercel файлы из public/ отдаёт CDN; эти маршруты — для локального запуска.
for _name in PUBLIC_FILES:
    app.add_url_rule(f"/{_name}", f"public_{_name}",
                     lambda n=_name: send_from_directory(PUBLIC_DIR, n, max_age=86400))


@app.route("/")
def index():
    selected = request.args.get("date")
    if not selected:
        today = date.today().isoformat()  # noqa: DTZ011 — запасной вариант без JS
        return LOCAL_DATE_REDIRECT.replace("{today}", today), 200, {
            "Content-Type": "text/html; charset=utf-8", "Cache-Control": CACHE_SHORT}

    try:
        day = date.fromisoformat(selected)
        if not FIRST_DAY <= day <= LAST_DAY:
            raise ValueError
    except ValueError:
        day = date.today()  # noqa: DTZ011
        return page(400, CACHE_SHORT,
                    error="Укажите дату в формате ГГГГ-ММ-ДД — с 14 марта 1900 "
                          "по 31 декабря 2099 года.",
                    iso=day.isoformat(), date_short="ошибка",
                    prev=(day - timedelta(days=1)).isoformat(),
                    next=(day + timedelta(days=1)).isoformat())

    ctx = {"iso": day.isoformat(), "date_short": day.strftime("%d.%m.%Y"),
           "prev": (day - timedelta(days=1)).isoformat(),
           "next": (day + timedelta(days=1)).isoformat()}
    try:
        reading = get_reading(day)
    except ValueError as exc:  # на случай непредвиденной даты вне расчёта
        return page(400, CACHE_SHORT, error=str(exc), **ctx)

    return page(r=reading, weekday=WEEKDAYS[day.weekday()].capitalize(),
                date_long=ru_date(day), old=old_style(day), error=None, **ctx)
