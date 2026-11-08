"""Локальный сервер Day 05: сравнение моделей small/medium/flagship."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import experiment_models as exp

ROOT = Path(__file__).resolve().parent / "web"
HOST = "127.0.0.1"
PORT = 8005


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/meta":
            self._json(
                200,
                {
                    "api_url": exp.API_URL,
                    "temperature": exp.TEMPERATURE,
                    "tiers": exp.MODEL_TIERS,
                    "tasks": [
                        {
                            "id": t["id"],
                            "kind": t["kind"],
                            "title": t["title"],
                            "prompt": t["prompt"],
                            "answer": t["answer"],
                        }
                        for t in exp.TASKS
                    ],
                    "calls_estimate": len(exp.MODEL_TIERS) * len(exp.TASKS)
                    + sum(len(t["candidates"]) for t in exp.MODEL_TIERS),
                },
            )
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/experiment":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            api_key = (payload.get("apiKey") or "").strip()
            if not api_key:
                raise ValueError("Нужен API-ключ.")
        except Exception as e:  # noqa: BLE001
            self._json(400, {"error": str(e)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send_event(obj: dict) -> None:
            self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()

        print("Experiment start (streaming)")
        try:
            def on_event(ev: dict) -> None:
                if ev.get("type") == "done":
                    return
                if ev.get("type") in {"progress", "rate_limit"}:
                    print(ev.get("message") or "")
                send_event(ev)

            result = exp.run_experiment(api_key, on_event=on_event)
            exp.save_artifacts(result)
            send_event(
                {
                    "type": "done",
                    "result": {
                        "api_url": result["api_url"],
                        "temperature": result["temperature"],
                        "models": result["models"],
                        "pricing_note": result["pricing_note"],
                        "tasks": result["tasks"],
                        "summary": result["summary"],
                        "conclusions": result["conclusions"],
                        "cells": result["cells"],
                        "report_markdown": result["report_markdown"],
                    },
                }
            )
            print("Experiment done")
        except Exception as e:  # noqa: BLE001
            send_event({"type": "error", "error": str(e)})
            print("Experiment error:", e)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"Day 05 — откройте http://{HOST}:{PORT}")
        httpd.serve_forever()
