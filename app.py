from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", phrase=TARGET_PHRASE)


@app.route("/api/hello/<name>")
def hello(name):
    return jsonify(message=f"Привіт, {name}!")


if __name__ == "__main__":
    app.run(debug=True)