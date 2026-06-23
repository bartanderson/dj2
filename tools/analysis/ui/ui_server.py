# tools/analysis/ui/ui_server.py
#
# Flask + SocketIO server for the developer console UI.
# Wraps the same _answer() pipeline as local_agent.py.
# Start via: python -m tools.analysis.agent.local_agent <corpus.db> --ui

from __future__ import annotations

import threading
from pathlib import Path

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor
from tools.analysis.agent.knowledge_status import coverage_summary

_TEMPLATE_DIR = str(Path(__file__).parent / "templates")
_STATIC_DIR   = str(Path(__file__).parent / "static")

app = Flask(__name__, template_folder=_TEMPLATE_DIR, static_folder=_STATIC_DIR)
app.config["SECRET_KEY"] = "dev-console-local"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# shared state (single-user local tool)
_oracle: DBOracle | None = None
_assessor: Assessor | None = None
_db_path: str = ""
_history: list[dict] = []
_lock = threading.Lock()


def init(db_path: str) -> None:
    global _oracle, _assessor, _db_path
    _oracle   = DBOracle(db_path)
    _assessor = Assessor(_oracle)
    _db_path  = db_path


@app.route("/")
def index():
    db_name = Path(_db_path).name if _db_path else "no corpus"
    summary = coverage_summary(_oracle, _assessor) if _oracle else ""
    return render_template("console.html", db_name=db_name, summary=summary)


@socketio.on("query")
def handle_query(data):
    global _history
    question = (data.get("question") or "").strip()
    if not question or _oracle is None:
        emit("error", {"message": "No question or corpus not loaded."})
        return

    emit("status", {"message": "Thinking..."})

    # import here to avoid circular at module level
    from tools.analysis.agent.local_agent import _answer

    try:
        with _lock:
            answer, _history = _answer(
                question, _history, _oracle, _assessor, verbose=False
            )
        emit("answer", {
            "question": question,
            "answer":   answer,
        })
    except Exception as exc:
        emit("error", {"message": f"Pipeline error: {exc}"})


@socketio.on("clear_history")
def handle_clear():
    global _history
    with _lock:
        _history = []
    emit("status", {"message": "History cleared."})


def run_server(db_path: str, host: str = "127.0.0.1", port: int = 5050) -> None:
    init(db_path)
    print(f"\nDev console: http://{host}:{port}")
    print(f"Corpus:       {db_path}")
    print(f"Press Ctrl+C to stop.\n")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
