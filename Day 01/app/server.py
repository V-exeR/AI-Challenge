"""Локальный сервер: раздаёт web/ и проксирует запросы к ai.wormsoft.ru."""

import json
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "web"
API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
MODEL = "wormsoft/agent/low"
HOST = "127.0.0.1"
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
            api_key = (payload.get("apiKey") or "").strip()
            prompt = (payload.get("prompt") or "").strip() or "Скажи привет в одном предложении."
            if not api_key:
                raise ValueError("Нужен API-ключ.")

            body = json.dumps(
                {
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                API_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                data = json.load(resp)

            content = data["choices"][0]["message"]["content"]
            self._json(200, {"content": content})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._json(e.code, {"error": f"HTTP {e.code}: {detail}"})
        except Exception as e:
            self._json(400, {"error": str(e)})

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
        print(f"Откройте http://{HOST}:{PORT}")
        httpd.serve_forever()
