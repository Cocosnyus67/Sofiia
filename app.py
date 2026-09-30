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
