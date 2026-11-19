import csv
import json
import os
import re
import threading
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, render_template, request
from sklearn.preprocessing import StandardScaler
from werkzeug.security import check_password_hash, generate_password_hash

import features  # беремо звідси готову функцію, яка рахує ознаки спроби

auth = Blueprint("auth", __name__)

PHRASE = "SS123+"                                         # пароль у демо = тренувальна фраза
ENROLL_ATTEMPTS = int(os.getenv("ENROLL_ATTEMPTS", "15"))  # скільки спроб треба для реєстрації
PERCENTILE = 77                                           # як будуємо поріг (пояснення нижче)
MAX_EVENTS = 200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
LOG_PATH = os.path.join(DATA_DIR, "login_log.csv")

# Ці поля не є ознаками ритму, у модель їх не віддаємо
SERVICE_FIELDS = ["user_id", "session_id", "attempt_id", "backspace_count", "error_count"]

_lock = threading.Lock()


# ---------- допоміжні функції ----------

def read_users():
    if not os.path.exists(USERS_PATH):
        return {}
    with open(USERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def check_events(events):
    """Повертає текст помилки або None, якщо все гаразд."""
    if not isinstance(events, list) or not events:
        return "Немає подій набору"
    if len(events) > MAX_EVENTS:
        return "Забагато подій"
    for ev in events:
        if not isinstance(ev, dict):
            return "Некоректна подія"
        if ev.get("type") not in ("down", "up"):
            return "type має бути down або up"
        if not isinstance(ev.get("code"), str) or not isinstance(ev.get("key"), str):
            return "Подія без key/code"
        if not isinstance(ev.get("t"), (int, float)) or ev["t"] < 0:
            return "Некоректний час події"
    return None


def get_features(events):
    """Перетворює події на словник ознак (як у features.py). None, якщо спроба невдала."""
    rows = []
    for i, ev in enumerate(events):
        rows.append({
            "user_id": "x", "session_id": "x", "attempt_id": "x",
            "event_idx": i, "type": ev["type"], "code": ev["code"], "t_ms": ev["t"],
            "backspace_count": 0, "error_count": 0,
        })
    return features.attempt_features(pd.DataFrame(rows))


def feature_columns(row):
    # як у models.py: службові поля й dd_* (вони дублюють ud_*) не беремо
    return [k for k in row if k not in SERVICE_FIELDS and not k.startswith("dd_")]


def profile_path(username):
    return os.path.join(PROFILES_DIR, username + ".pkl")


def train_profile(username, samples, cols):
    """Профіль = усі спроби власника + поріг відстані.

    Ідея проста: нова спроба "своя", якщо вона схожа хоча б на одну зі спроб власника.
    Схожість = відстань між наборами ознак (чим менша, тим схожіші).
    Поріг: дивимось, на якій відстані власні спроби стоять одна від одної,
    і беремо 85-й перцентиль (так ~85% своїх спроб проходять).
    """
    scaler = StandardScaler().fit(pd.DataFrame(samples, columns=cols))
    T = scaler.transform(pd.DataFrame(samples, columns=cols))

    nearest = []
    for i in range(len(T)):
        d = np.linalg.norm(T - T[i], axis=1)
        d[i] = np.inf                      # саму себе не рахуємо
        nearest.append(d.min())
    threshold = float(np.percentile(nearest, PERCENTILE))

    os.makedirs(PROFILES_DIR, exist_ok=True)
    joblib.dump({"scaler": scaler, "samples": T, "threshold": threshold, "cols": cols},
                profile_path(username))


def write_log(username, access, distance, reason):
    os.makedirs(DATA_DIR, exist_ok=True)
    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["time", "username", "access", "distance", "reason"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), username, access, distance, reason])


def valid_username(name):
    return isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name) is not None


# ---------- сторінки ----------

@auth.route("/login")
def login_page():
    return render_template("login.html", mode="login", phrase=PHRASE, needed=ENROLL_ATTEMPTS)


@auth.route("/register")
def register_page():
    return render_template("login.html", mode="register", phrase=PHRASE, needed=ENROLL_ATTEMPTS)


# ---------- реєстрація: одна спроба = один запит ----------

@auth.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Очікувався JSON"), 400

    username = data.get("username", "")
    password = data.get("password", "")
    events = data.get("events")

    if not valid_username(username):
        return jsonify(ok=False, error="Логін: лише латиниця, цифри, _ або - (до 32 символів)"), 400

    error = check_events(events)
    if error:
        return jsonify(ok=False, error=error), 400

    with _lock:
        users = read_users()
        user = users.get(username)

        if user is None:
            if password != PHRASE:
                return jsonify(ok=False, error="Пароль у демо має бути: " + PHRASE), 400
        else:
            if user["ready"]:
                return jsonify(ok=False, error="Цей логін уже зареєстровано"), 409
            if not check_password_hash(user["password_hash"], password):
                return jsonify(ok=False, error="Невірний пароль"), 401

        row = get_features(events)
        if row is None:
            return jsonify(ok=False,
                           error="Спробу набрано з виправленнями. Очисти поле й набери ще раз"), 400

        cols = feature_columns(row)
        if user is None:
            user = {
                "password_hash": generate_password_hash(password),
                "created": datetime.now().isoformat(timespec="seconds"),
                "cols": cols,
                "samples": [],
                "ready": False,
            }
            users[username] = user

        user["samples"].append([row[c] for c in user["cols"]])

        if len(user["samples"]) >= ENROLL_ATTEMPTS:
            train_profile(username, user["samples"], user["cols"])
            user["ready"] = True

        save_users(users)
        count = len(user["samples"])
        ready = user["ready"]

    return jsonify(ok=True, count=count, needed=ENROLL_ATTEMPTS, ready=ready)


# ---------- вхід ----------

@auth.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="Очікувався JSON"), 400

    username = data.get("username", "")
    password = data.get("password", "")
    events = data.get("events")

    if not valid_username(username) or not isinstance(password, str):
        return jsonify(ok=True, access=False, reason="Невірний логін або пароль")

    error = check_events(events)
    if error:
        return jsonify(ok=False, error=error), 400

    users = read_users()
    user = users.get(username)

    # 1) спочатку пароль (про те, що логіна нема, не кажемо окремо)
    if user is None or not check_password_hash(user["password_hash"], password):
        write_log(username, False, "", "невірний логін або пароль")
        return jsonify(ok=True, access=False, reason="Невірний логін або пароль")

    if not user["ready"]:
        left = ENROLL_ATTEMPTS - len(user["samples"])
        reason = "Реєстрацію не завершено: потрібно ще " + str(left) + " спроб"
        return jsonify(ok=True, access=False, reason=reason)

    # 2) потім ритм набору
    row = get_features(events)
    if row is None:
        return jsonify(ok=True, access=False,
                       reason="Фразу набрано з виправленнями. Спробуй ще раз без Backspace")

    profile = joblib.load(profile_path(username))
    X = pd.DataFrame([[row[c] for c in profile["cols"]]], columns=profile["cols"])
    x = profile["scaler"].transform(X)[0]
    distance = float(np.linalg.norm(profile["samples"] - x, axis=1).min())   # до найближчої своєї спроби
    threshold = profile["threshold"]
    access = distance <= threshold

    if access:
        reason = "Пароль правильний, ритм набору схожий на твій профіль"
    else:
        reason = "Пароль правильний, але ритм набору не схожий на профіль цього користувача"

    write_log(username, access, round(distance, 3), reason)
    return jsonify(ok=True, access=access, reason=reason,
                   distance=round(distance, 2), threshold=round(threshold, 2))
