"""Локальный сервер Day 02: web UI эксперимента контроля ответа."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import experiment_control as exp

ROOT = Path(__file__).resolve().parent / "web"
HOST = "127.0.0.1"
PORT = 8001


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/meta":
            self._json(
                200,
                {
                    "model": exp.MODEL,
                    "api_url": exp.API_URL,
                    "base_prompt": exp.BASE_PROMPT,
                    "variants": [
                        {"id": v["id"], "title": v["title"], "extra": v["extra"]}
                        for v in exp.VARIANTS
                    ],
                    "default_runs": exp.RUNS,
                },
            )
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/experiment":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            api_key = (payload.get("apiKey") or "").strip()
            runs = int(payload.get("runs") or exp.RUNS)
            prompt = (payload.get("prompt") or "").strip() or exp.BASE_PROMPT
            if not api_key:
                raise ValueError("Нужен API-ключ.")

            print(f"Experiment start: runs={runs}; prompt={prompt!r}")
            result = exp.run_experiment(api_key, runs=runs, base_prompt=prompt)
            exp.save_artifacts(result)
            self._json(
                200,
                {
                    "model": result["model"],
                    "runs": result["runs"],
                    "base_prompt": result["base_prompt"],
                    "comparison": result["comparison"],
                    "conclusions": result["conclusions"],
                    "report_markdown": result["report_markdown"],
                },
            )
            print(f"Experiment done; used_prompt={result['base_prompt']!r}")
        except Exception as e:  # noqa: BLE001
            self._json(400, {"error": str(e)})

    def end_headers(self):
        # Чтобы браузер не держал старый app.js после правок.
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
        print(f"Day 02 — откройте http://{HOST}:{PORT}")
        httpd.serve_forever()
