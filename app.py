from datetime import date
from html import escape

from flask import Flask, request

from src.readings import get_reading

app = Flask(__name__)


HTML = """<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Чтения дня</title>
    <style>
        :root {
            color-scheme: light;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        body {
            margin: 0;
            background: #f5f3ef;
            color: #222;
        }

        main {
            max-width: 760px;
            margin: 0 auto;
            padding: 48px 20px;
        }

        .card {
            background: white;
            border-radius: 18px;
            padding: 28px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, .08);
        }

        h1 {
            margin-top: 0;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 28px;
        }

        form {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 28px;
        }

        input, button {
            font: inherit;
            padding: 11px 14px;
            border-radius: 10px;
            border: 1px solid #ccc;
        }

        input {
            flex: 1;
            min-width: 180px;
        }

        button {
            background: #222;
            color: white;
            border-color: #222;
            cursor: pointer;
        }

        pre {
            white-space: pre-wrap;
            line-height: 1.6;
            font-family: inherit;
            margin: 0;
        }

        .error {
            color: #a33;
            background: #fff0f0;
            padding: 14px;
            border-radius: 10px;
        }
    </style>
</head>
<body>
<main>
    <div class="card">
        <h1>Чтения дня</h1>
        <div class="subtitle">
            Евангелие и Апостол по дате
        </div>

        <form method="get">
            <input
                type="date"
                name="date"
                value="{selected_date}"
                required
            >
            <button type="submit">Показать чтения</button>
        </form>

        {content}
    </div>
</main>
</body>
</html>
"""


@app.route("/")
def index():
    selected_date = request.args.get("date") or date.today().isoformat()

    try:
        day = date.fromisoformat(selected_date)
        reading = get_reading(day)
        content = f"<pre>{escape(reading.format())}</pre>"
    except ValueError:
        content = '<div class="error">Некорректная дата. Используйте формат ГГГГ-ММ-ДД.</div>'
    except Exception as exc:
        content = f'<div class="error">Для этой даты пока нет данных: {escape(str(exc))}</div>'

    return HTML.replace(
    "{selected_date}", escape(selected_date)
).replace(
    "{content}", content
)