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
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
