"""
app.py - lightweight demo UI for the assignment.

Serves the pre-computed pipeline output (output/*.json). It NEVER reads the
raw messages.csv -> only the display-safe display_messages.json (sensitive
messages are already masked before this file was written), so there is no
way for a raw secret to be rendered by this app, even by accident.

Run locally:
    pip install -r requirements.txt
    python3 app.py
    -> http://localhost:5000

Deploy (free options, pick one, ~5 min each):
    - Render.com          : "New Web Service" -> connect repo -> build
                             command `pip install -r requirements.txt`,
                             start command `python app.py`.
    - Railway.app         : "New Project" -> "Deploy from GitHub repo".
    - PythonAnywhere      : upload files, create a Flask web app pointing
                             at app.py.
"""

import json
import os
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")

app = Flask(__name__)


def load(name):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path) as f:
        return json.load(f)


@app.route("/")
def index():
    summary = load("summary.json")
    return render_template("index.html", summary=summary)


@app.route("/messages")
def messages():
    category = request.args.get("category", "all")
    data = load("display_messages.json")
    if category != "all":
        data = [m for m in data if m["category"] == category]
    return render_template("messages.html", messages=data[:200], category=category)


@app.route("/tasks-events")
def tasks_events():
    kind = request.args.get("type", "all")
    data = load("tasks_events.json")
    if kind != "all":
        data = [d for d in data if d["type"] == kind]
    return render_template("tasks_events.html", items=data, kind=kind)


@app.route("/sensitive")
def sensitive():
    data = load("sensitive_findings.json")
    return render_template("sensitive.html", findings=data)


@app.route("/mandatory")
def mandatory():
    data = load("mandatory_ids_report.json")
    return render_template("mandatory.html", items=data)


@app.route("/api/summary")
def api_summary():
    return jsonify(load("summary.json"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
