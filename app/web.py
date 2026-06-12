#!/usr/bin/env python3

import os
from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)

# SQLite DB lives in the shared volume (mounted at /app inside the container)
DB_PATH = Path(os.getenv("JOB_REPO_DB", "/app/job_repo.db"))


def init_db():
    # Ensure the database and required tables exist
    if not DB_PATH.exists():
        import sqlite3

        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                size INTEGER,
                mtime REAL,
                status TEXT NOT NULL,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        """)
        conn.close()


if os.getenv("FLASK_ENV") != "testing":
    init_db()


HTML = """
<!doctype html>
<title>Transcode Jobs</title>
<h1>Job status</h1>
<table border=1 cellpadding=5>
  <tr><th>ID</th><th>Path</th><th>Status</th><th>Error</th></tr>
  {% for j in jobs %}
    <tr>
      <td>{{j.id}}</td>
      <td>{{j.path}}</td>
      <td>{{j.status}}</td>
      <td>{{j.error or ''}}</td>
    </tr>
  {% endfor %}
</table>

<h2>Actions</h2>
<form method="post" action="{{ url_for('trigger_all') }}">
  <button type="submit">Transcode ALL</button>
</form>

<form method="post" action="{{ url_for('trigger_one') }}">
  <input name="path" placeholder="Full absolute path to media file" size="80" required>
  <button type="submit">Transcode ONE</button>
</form>
"""


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    with _get_db() as conn:
        jobs = conn.execute(
            "SELECT id, path, status, error FROM jobs ORDER BY id"
        ).fetchall()
    return render_template_string(HTML, jobs=jobs)


@app.route("/trigger/all", methods=["POST"])
def trigger_all():
    # Create the trigger file that the host watcher monitors
    Path("/app/trigger_all").touch()
    return redirect(url_for("index"))


@app.route("/trigger/one", methods=["POST"])
def trigger_one():
    # Path submitted by user; encode slashes as underscores for a safe filename
    raw_path = request.form["path"].strip()
    safe_name = "trigger_" + raw_path.replace("/", "_")
    Path(f"/app/{safe_name}").touch()
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Port can be overridden by env var FLASK_PORT; defaults to 5577
    port = int(os.getenv("FLASK_PORT", "5577"))
    app.run(host="0.0.0.0", port=port)
