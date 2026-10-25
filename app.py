from datetime import date, timedelta

from flask import Flask, render_template_string, request

from src.readings import get_reading

app = Flask(__name__)

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница",
            "суббота", "воскресенье"]


def ru_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def old_style(d: date) -> str:
    """Дата по старому стилю (разница 13 дней в 1900–2099 гг.)."""
    o = d - timedelta(days=13)
    return f"{o.day}\u00a0{MONTHS[o.month - 1]} ст.\u00a0ст."


PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Чтения дня — {{ date_short }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=PT+Serif:ital,wght@0,400;0,700;1,400&family=PT+Sans:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f6f1e7; --card: #fffdf8; --ink: #2a2420; --muted: #7a6f63;
    --line: #e4dccd; --accent: #a3271d; --accent-soft: #f3e3dc; --note: #f1ebde;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1b1916; --card: #24211d; --ink: #ece4d6; --muted: #a59a8a;
      --line: #3a352e; --accent: #e07a62; --accent-soft: #3a2621; --note: #2c2823;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 17px/1.55 "PT Sans", system-ui, sans-serif; }
  main { max-width: 640px; margin: 0 auto; padding: 24px 16px 48px; }
  nav { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
  nav a, nav button, nav input {
    font: inherit; font-size: 15px; color: var(--ink); background: var(--card);
    border: 1px solid var(--line); border-radius: 999px; padding: 7px 14px;
    text-decoration: none; cursor: pointer; }
  nav a.arrow { padding: 7px 12px; }
  nav form { display: flex; gap: 8px; margin-left: auto; }
  nav input { padding: 6px 10px; max-width: 150px; }
  .date { color: var(--muted); font-size: 15px; margin: 0; }
  .date b { color: var(--ink); font-weight: 700; }
  h1 { font: 700 28px/1.25 "PT Serif", Georgia, serif; margin: 6px 0 4px; }
  .subtitle { font-family: "PT Serif", Georgia, serif; font-style: italic;
              color: var(--muted); margin: 0 0 20px; }
  .card { background: var(--card); border: 1px solid var(--line);
          border-radius: 14px; overflow: hidden; }
  .reading { display: block; padding: 16px 18px; border-top: 1px solid var(--line);
             color: inherit; text-decoration: none; }
  .reading:first-child { border-top: 0; }
  a.reading:hover { background: var(--accent-soft); }
  .label { font-size: 13px; text-transform: uppercase; letter-spacing: .06em;
           color: var(--accent); font-weight: 700; }
  .ref { font: 400 22px/1.3 "PT Serif", Georgia, serif; margin-top: 2px; }
  .ref .go { color: var(--accent); font-size: 18px; }
  .zach { color: var(--muted); font-size: 15px; }
  .missing { color: var(--muted); font-style: italic; margin-top: 2px; }
  .notes { margin: 16px 0 0; padding: 0; list-style: none; }
  .notes li { background: var(--note); border-radius: 10px; padding: 10px 14px;
              margin-top: 8px; font-size: 15px; color: var(--muted); }
  .unresolved { padding: 18px; color: var(--muted); }
  .service { padding: 10px 18px 8px; font: italic 15px/1.3 "PT Serif", Georgia, serif;
             color: var(--muted); background: var(--note); border-top: 1px solid var(--line); }
  .service:first-child { border-top: 0; }
  .service + .reading { border-top: 0; }
  .part { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
          color: inherit; text-decoration: none; margin-top: 4px; }
  .part .ref { font-size: 19px; }
  .part:hover .ref { color: var(--accent); }
  footer { margin-top: 28px; font-size: 14px; color: var(--muted); }
  footer a { color: var(--accent); }
  @media (max-width: 480px) {
    nav { flex-wrap: wrap; }
    nav form { margin-left: 0; width: 100%; }
    nav input { max-width: none; flex: 1; }
    h1 { font-size: 24px; }
  }
</style>
</head>
<body>
<main>
  <nav>
    <a class="arrow" href="?date={{ prev }}" aria-label="Предыдущий день">←</a>
    <a href="/">Сегодня</a>
    <a class="arrow" href="?date={{ next }}" aria-label="Следующий день">→</a>
    <form method="get">
      <input type="date" name="date" value="{{ iso }}" required aria-label="Дата">
      <button type="submit">Показать</button>
    </form>
  </nav>

  {% if error %}
    <div class="card"><div class="unresolved">{{ error }}</div></div>
  {% else %}
    <p class="date"><b>{{ weekday }}, {{ date_long }}</b> · {{ old }}</p>
    <h1>{{ r.title }}</h1>
    {% if r.note %}<p class="subtitle">{{ r.note }}</p>{% else %}<div style="height:12px"></div>{% endif %}

    <div class="card">
      {% for service, items in r.groups %}
        {% if service %}<div class="service">{{ service }}</div>{% endif %}
        {% for i in items %}
          {% if i.parts %}
          <div class="reading">
            <div class="label">{{ i.label }}</div>
            {% for p in i.parts %}
            <a class="part" href="{{ p.url }}" target="_blank" rel="noopener">
              <span class="ref">{{ p.ref }} <span class="go">↗</span></span>
              {% if p.zachalo %}<span class="zach">зач. {{ p.zachalo }}</span>{% endif %}
            </a>
            {% endfor %}
          </div>
          {% elif i.url %}
          <a class="reading" href="{{ i.url }}" target="_blank" rel="noopener">
            <div class="label">{{ i.label }}</div>
            <div class="ref">{{ i.ref }} <span class="go">↗</span></div>
            {% if i.zachalo %}<div class="zach">зачало {{ i.zachalo }}</div>{% endif %}
          </a>
          {% else %}
          <div class="reading">
            <div class="label">{{ i.label }}</div>
            {% if i.ref %}<div class="ref">{{ i.ref }}</div>
            {% else %}<div class="missing">{{ i.missing }}</div>{% endif %}
          </div>
          {% endif %}
        {% endfor %}
      {% else %}
        <div class="unresolved">Рядовые чтения на этот день приложение пока не выдаёт. <a href="{{ r.azbyka_day_url }}" target="_blank" rel="noopener" style="color:var(--accent)">Чтения дня на «Азбуке веры» ↗</a></div>
      {% endfor %}
    </div>

    {% if r.notes %}
    <ul class="notes">{% for n in r.notes|unique %}<li>{{ n }}</li>{% endfor %}</ul>
    {% endif %}

    <footer>
      Показаны рядовые чтения, Триодь постная и двунадесятые праздники (без чтений святых по Минее).
      Все чтения дня — <a href="{{ r.azbyka_day_url }}" target="_blank" rel="noopener">на «Азбуке веры»</a>.
      Ссылки открывают Синодальный перевод.
    </footer>
  {% endif %}
</main>
</body>
</html>
"""

# Сервер (Vercel) работает в UTC, а «сегодня» у читателя — по его часовому
# поясу. Если дата не передана, страница сама подставляет локальную дату.
LOCAL_DATE_REDIRECT = """<!doctype html><meta charset="utf-8">
<script>
var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
location.replace("?date=" + d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()));
</script>
<noscript><meta http-equiv="refresh" content="0; url=?date={today}"></noscript>
"""


@app.route("/")
def index():
    selected = request.args.get("date")
    if not selected:
        return LOCAL_DATE_REDIRECT.replace("{today}", date.today().isoformat())

    try:
        day = date.fromisoformat(selected)
    except ValueError:
        day = date.today()
        return render_template_string(
            PAGE, error="Некорректная дата. Используйте формат ГГГГ-ММ-ДД.",
            iso=day.isoformat(), date_short="ошибка",
            prev=(day - timedelta(days=1)).isoformat(),
            next=(day + timedelta(days=1)).isoformat()), 400

    ctx = dict(iso=day.isoformat(), date_short=day.strftime("%d.%m.%Y"),
               prev=(day - timedelta(days=1)).isoformat(),
               next=(day + timedelta(days=1)).isoformat())
    try:
        reading = get_reading(day)
    except ValueError as exc:  # например, год вне 1900–2099
        return render_template_string(PAGE, error=str(exc), **ctx), 400

    return render_template_string(
        PAGE, r=reading, weekday=WEEKDAYS[day.weekday()].capitalize(),
        date_long=ru_date(day), old=old_style(day), error=None, **ctx)
