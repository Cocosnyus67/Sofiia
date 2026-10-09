import csv
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

TARGET_PHRASE = "SS123+"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "attempts.csv")


@app.route("/")
def index():
    return render_template("index.html", phrase=TARGET_PHRASE)


@app.route("/api/hello/<name>")
def hello(name):
    return jsonify(message=f"Привіт, {name}!")


@app.route("/collect", methods=["POST"])
def collect():
    data = request.get_json()
    

    user_id = data["user_id"]
    attempt_id = data["attempt_id"]

    now = datetime.now().isoformat(timespec="seconds")

    for i, e in enumerate(data["events"]):
        row = [
            user_id,
            attempt_id,
            now,
            e["key"],
            e["type"],
            i,
            e["t"],
            data["backspace_count"],
            data["error_count"]
        ]    

        print(row)

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for key, event_type, idx, t_ms in cleaned_events:
                writer.writerow([
                    user_id, attempt_id, timestamp_server,
                    key, event_type, idx, t_ms,
                    backspace_count, error_count,
                ])


    return jsonify({
        "ok": True,
        "saved_events": len(data["events"])
    })




if __name__ == "__main__":
    app.run(debug=True)