import csv
import os
import re
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

TARGET_PHRASE = "SS123+"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "attempts.csv")

CSV_HEADER = [
    "user_id", "session_id", "attempt_id", "server_time", "keyboard_type",
    "user_agent", "event_idx", "key", "code", "type", "t_ms",
    "backspace_count", "error_count",
]

KEYBOARD_TYPES = {"laptop", "external", "other"}
MAX_EVENTS = 200

_write_lock = threading.Lock()

class ValidationError(Exception):
    pass


def validate(data):
    if not isinstance(data, dict):
        raise ValidationError("Очікувався JSON-об'єкт")

    for field in ("user_id", "session_id", "attempt_id"):
        if not isinstance(data.get(field), str):
            raise ValidationError(
                f"Поле {field} має містити лише літери, цифри, _ або - (до 32 символів)"
            )

    keyboard = data.get("keyboard_type", "other")
    if keyboard not in KEYBOARD_TYPES:
        raise ValidationError("Невірний keyboard_type")

    for field in ("backspace_count", "error_count"):
        if not isinstance(data.get(field), int) or data[field] < 0:
            raise ValidationError(f"Поле {field} має бути невід'ємним цілим")

    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise ValidationError("Список events порожній")
    if len(events) > MAX_EVENTS:
        raise ValidationError("Забагато подій у спробі")

    downs = ups = 0
    for ev in events:
        if not isinstance(ev, dict):
            raise ValidationError("Некоректна подія")
        if ev.get("type") not in ("down", "up"):
            raise ValidationError("type має бути down або up")
        if not isinstance(ev.get("key"), str) or not isinstance(ev.get("code"), str):
            raise ValidationError("Подія без key/code")
        if not isinstance(ev.get("t"), (int, float)) or ev["t"] < 0:
            raise ValidationError("Некоректний час події")
        if ev["type"] == "down":
            downs += 1
        else:
            ups += 1
    if downs != ups:
        raise ValidationError("Кількість down і up не збігається")

    return {
        "user_id": data["user_id"],
        "session_id": data["session_id"],
        "attempt_id": data["attempt_id"],
        "keyboard_type": keyboard,
        "user_agent": str(data.get("user_agent", ""))[:200],
        "backspace_count": data["backspace_count"],
        "error_count": data["error_count"],
        "events": events,
    }


@app.route("/")
def index():
    return render_template("index.html", phrase=TARGET_PHRASE)


@app.route("/collect", methods=["POST"])
def collect():
    try:
        clean = validate(request.get_json(silent=True))
    except ValidationError as e:
        return jsonify(ok=False, error=str(e)), 400

    now = datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA_DIR, exist_ok=True)

    rows = [
        [
            clean["user_id"], clean["session_id"], clean["attempt_id"], now,
            clean["keyboard_type"], clean["user_agent"], i,
            ev["key"], ev["code"], ev["type"], round(ev["t"], 3),
            clean["backspace_count"], clean["error_count"],
        ]
        for i, ev in enumerate(clean["events"])
    ]

    try:
         with _write_lock:
            new_file = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
            with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(CSV_HEADER)
                writer.writerows(rows)
    except OSError:
        return jsonify(ok=False, error="Не вдалося записати файл на сервері"), 500

    return jsonify(ok=True, saved_events=len(rows))


if __name__ == "__main__":
     app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=5000,
        debug=os.getenv("FLASK_DEBUG") == "1",
    )