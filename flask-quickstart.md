# Flask: швидкий старт

Покрокова інструкція зі встановлення Flask та створення найпростішого проєкту (Windows, PowerShell).

## Що таке Flask

Flask — мінімалістичний веб-фреймворк для Python. Він надає лише базові речі (маршрутизація, обробка запитів, шаблони Jinja2), а решту (база даних, авторизація, форми) можна додати через розширення.

## Вимоги

- Python 3.9 або новіший
- pip (встановлюється разом із Python)

Перевірка версії:

```powershell
python --version
pip --version
```

## Крок 1. Створіть папку проєкту

```powershell
mkdir flask-demo
cd flask-demo
```

## Крок 2. Створіть віртуальне середовище

```powershell
python -m venv venv
```

## Крок 3. Активуйте віртуальне середовище

```powershell
venv\Scripts\Activate.ps1
```

Якщо PowerShell забороняє запуск скриптів, виконайте один раз:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Після активації на початку рядка з'явиться `(venv)`.

## Крок 4. Встановіть Flask

```powershell
pip install flask
```

Збережіть залежності у файл:

```powershell
pip freeze > requirements.txt
```

## Крок 5. Створіть файл `app.py`

```python
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return "Привіт, Flask!"


@app.route("/api/hello/<name>")
def hello(name):
    return jsonify(message=f"Привіт, {name}!")


if __name__ == "__main__":
    app.run(debug=True)
```

## Крок 6. Запустіть застосунок

```powershell
python app.py
```

Сервер запуститься на `http://127.0.0.1:5000`.

## Крок 7. Перевірте результат

- `http://127.0.0.1:5000/` — текст «Привіт, Flask!»
- `http://127.0.0.1:5000/api/hello/Ihor` — JSON: `{"message": "Привіт, Ihor!"}`

Зупинити сервер: `Ctrl + C`.

## Як це працює

| Елемент | Призначення |
|---|---|
| `Flask(__name__)` | створює застосунок |
| `@app.route("/...")` | прив'язує URL до функції |
| `return "..."` | рядок, HTML або JSON стає відповіддю |
| `debug=True` | автоперезапуск при зміні коду та показ помилок у браузері |

> **Увага:** `debug=True` використовуйте лише під час розробки, у продакшені його вмикати не можна.

## Додаємо HTML-шаблон

Структура проєкту:

```
flask-demo/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    └── style.css
```

`templates/index.html`:

```html
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Це сторінка з шаблону Jinja2.</p>
</body>
</html>
```

`static/style.css`:

```css
body {
    font-family: sans-serif;
    margin: 2rem;
}
```

Додайте маршрут у `app.py`:

```python
from flask import render_template


@app.route("/page")
def page():
    return render_template("index.html", title="Моя сторінка")
```

Відкрийте `http://127.0.0.1:5000/page`.

## Корисні команди

| Дія | Команда |
|---|---|
| Активувати venv | `venv\Scripts\Activate.ps1` |
| Вийти з venv | `deactivate` |
| Встановити залежності з файлу | `pip install -r requirements.txt` |
| Запуск через Flask CLI | `flask --app app run --debug` |

## Типові проблеми

- **`python` не знайдено** — переінсталюйте Python із позначкою «Add Python to PATH».
- **Порт 5000 зайнятий** — змініть порт: `app.run(debug=True, port=5001)`.
- **`ModuleNotFoundError: No module named 'flask'`** — перевірте, що віртуальне середовище активоване (`(venv)` у рядку).

## Наступні кроки

- База даних: Flask-SQLAlchemy
- Форми: Flask-WTF
- Авторизація: Flask-Login
- REST API: Flask-RESTful або Flask-Smorest
- Розгортання: Gunicorn (Linux) або Waitress (Windows)
