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

## Запуск у контейнері

```powershell
docker compose up --build
```
