"""Минимальный CLI: запрос в LLM через ai.wormsoft.ru → ответ в консоль."""

import getpass
import json
import sys
import urllib.error
import urllib.request

API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
MODEL = "wormsoft/agent/low"

api_key = getpass.getpass("API key: ").strip()
if not api_key:
    sys.exit("Нужен API-ключ.")

prompt = " ".join(sys.argv[1:]) or "Скажи привет в одном предложении."

body = json.dumps(
    {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
).encode("utf-8")

request = urllib.request.Request(
    API_URL,
    data=body,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request) as response:
        data = json.load(response)
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")

print(data["choices"][0]["message"]["content"])
