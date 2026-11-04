"""Прогон одного запроса с разным уровнем контроля ответа."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
MODEL = "wormsoft/agent/low"
RUNS = 3
TIMEOUT_SEC = 90

BASE_PROMPT = (
    "Опиши язык программирования Python: что это, для чего используют, "
    "и назови ровно три ключевые особенности."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "Краткое описание Python"},
        "uses": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
            "description": "Области применения",
        },
        "features": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
            "description": "Ровно три ключевые особенности",
        },
    },
    "required": ["summary", "uses", "features"],
    "additionalProperties": False,
}

VARIANTS = [
    {
        "id": "baseline",
        "title": "Без ограничений",
        "messages": [{"role": "user", "content": BASE_PROMPT}],
        "extra": {},
    },
    {
        "id": "format_prompt",
        "title": "Явное описание формата в промпте",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"{BASE_PROMPT}\n\n"
                    "Ответь строго в таком виде (без Markdown и без лишнего текста):\n"
                    "SUMMARY: <одно предложение>\n"
                    "USES: <через запятую>\n"
                    "FEATURES:\n"
                    "1. <особенность>\n"
                    "2. <особенность>\n"
                    "3. <особенность>"
                ),
            }
        ],
        "extra": {},
    },
    {
        "id": "max_tokens",
        "title": "Ограничение объёма (max_tokens=40)",
        "messages": [{"role": "user", "content": BASE_PROMPT}],
        "extra": {"max_tokens": 40},
    },
    {
        "id": "stop",
        "title": "Stop sequence",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"{BASE_PROMPT}\n\n"
                    "Структура ответа:\n"
                    "ЧАСТЬ1: краткое описание\n"
                    "STOPHERE\n"
                    "ЧАСТЬ2: особенности (не должна появиться)"
                ),
            }
        ],
        "extra": {"stop": ["STOPHERE", "\nSTOPHERE"]},
    },
    {
        "id": "json_schema",
        "title": "Строгая схема (response_format json_schema)",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"{BASE_PROMPT}\n\n"
                    "Верни только JSON-объект со полями summary, uses, features."
                ),
            }
        ],
        "extra": {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "python_overview",
                    "strict": True,
                    "schema": SCHEMA,
                },
            }
        },
    },
]


def load_api_key() -> str:
    key = (os.getenv("WORMSOFT_API_KEY") or "").strip()
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        bare = None
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                name, value = line.split("=", 1)
                if name.strip() in {"WORMSOFT_API_KEY", "API_KEY", "OPENAI_API_KEY"}:
                    return value.strip().strip('"').strip("'")
            elif bare is None:
                bare = line.strip('"').strip("'")
        if bare:
            return bare
    sys.exit("Нет WORMSOFT_API_KEY в окружении или .env")


def chat(api_key: str, messages: list, extra: dict) -> dict:
    body = {"model": MODEL, "messages": messages, "stream": False, **extra}
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=raw,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            data = json.load(resp)
        choice = data["choices"][0]
        content = choice.get("message", {}).get("content")
        return {
            "ok": True,
            "content": content if content is not None else "",
            "finish_reason": choice.get("finish_reason"),
            "model": data.get("model"),
            "usage": data.get("usage"),
            "error": None,
            "raw_choice": choice,
        }
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "content": "",
            "finish_reason": None,
            "model": None,
            "usage": None,
            "error": f"HTTP {e.code}: {detail}",
            "raw_choice": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "content": "",
            "finish_reason": None,
            "model": None,
            "usage": None,
            "error": str(e),
            "raw_choice": None,
        }


def try_parse_json(text: str) -> tuple[bool, object | None, str]:
    if not text or not str(text).strip():
        return False, None, "пустой ответ"
    s = str(text).strip()
    # снять markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if fence:
        s = fence.group(1).strip()
    try:
        obj = json.loads(s)
        return True, obj, "json.loads OK"
    except json.JSONDecodeError as e:
        # попытка вырезать первый объект
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(s[start : end + 1])
                return True, obj, "json.loads после вырезки {...}"
            except json.JSONDecodeError as e2:
                return False, None, f"JSONDecodeError: {e2}"
        return False, None, f"JSONDecodeError: {e}"


def validate_schema(obj: object) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "не объект"
    missing = [k for k in ("summary", "uses", "features") if k not in obj]
    if missing:
        return False, f"нет полей: {missing}"
    if any(k not in SCHEMA["properties"] for k in obj):
        extras = [k for k in obj if k not in SCHEMA["properties"]]
        return False, f"лишние поля: {extras}"
    if not isinstance(obj["summary"], str):
        return False, "summary не string"
    if not isinstance(obj["uses"], list) or not all(isinstance(x, str) for x in obj["uses"]):
        return False, "uses не array[string]"
    if not isinstance(obj["features"], list) or not all(
        isinstance(x, str) for x in obj["features"]
    ):
        return False, "features не array[string]"
    if len(obj["features"]) != 3:
        return False, f"features len={len(obj['features'])}, нужно 3"
    return True, "схема OK"


def parse_format_prompt(text: str) -> tuple[bool, str]:
    if not text:
        return False, "пусто"
    ok_summary = bool(re.search(r"(?im)^SUMMARY:\s*.+", text))
    ok_uses = bool(re.search(r"(?im)^USES:\s*.+", text))
    feats = re.findall(r"(?im)^\s*[123]\.\s*.+", text)
    if ok_summary and ok_uses and len(feats) >= 3:
        return True, "формат SUMMARY/USES/FEATURES соблюдён"
    parts = []
    if not ok_summary:
        parts.append("нет SUMMARY")
    if not ok_uses:
        parts.append("нет USES")
    if len(feats) < 3:
        parts.append(f"features={len(feats)}")
    return False, "; ".join(parts)


def md_escape(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def run_variant_once(api_key: str, variant: dict) -> dict:
    t0 = time.time()
    out = chat(api_key, variant["messages"], variant["extra"])
    elapsed = round(time.time() - t0, 2)
    content = out["content"] if out["content"] is not None else ""
    parsed_ok, parsed_obj, parse_note = try_parse_json(content)
    schema_ok, schema_note = (False, "n/a")
    if parsed_ok:
        schema_ok, schema_note = validate_schema(parsed_obj)
    format_ok, format_note = parse_format_prompt(content)
    return {
        **{k: v for k, v in out.items() if k != "raw_choice"},
        "elapsed_sec": elapsed,
        "chars": len(content),
        "json_parse_ok": parsed_ok,
        "json_parse_note": parse_note,
        "schema_ok": schema_ok,
        "schema_note": schema_note,
        "format_ok": format_ok,
        "format_note": format_note,
        "contains_stop_marker": "STOPHERE" in content,
    }


def build_variants(base_prompt: str) -> list[dict]:
    """Те же 5 уровней контроля, но с произвольным базовым запросом."""
    base = (base_prompt or "").strip() or BASE_PROMPT
    return [
        {
            "id": "baseline",
            "title": "Без ограничений",
            "messages": [{"role": "user", "content": base}],
            "extra": {},
        },
        {
            "id": "format_prompt",
            "title": "Явное описание формата в промпте",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"{base}\n\n"
                        "Ответь строго в таком виде (без Markdown и без лишнего текста):\n"
                        "SUMMARY: <одно предложение>\n"
                        "USES: <через запятую>\n"
                        "FEATURES:\n"
                        "1. <особенность>\n"
                        "2. <особенность>\n"
                        "3. <особенность>"
                    ),
                }
            ],
            "extra": {},
        },
        {
            "id": "max_tokens",
            "title": "Ограничение объёма (max_tokens=40)",
            "messages": [{"role": "user", "content": base}],
            "extra": {"max_tokens": 40},
        },
        {
            "id": "stop",
            "title": "Stop sequence",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"{base}\n\n"
                        "Структура ответа:\n"
                        "ЧАСТЬ1: краткое описание\n"
                        "STOPHERE\n"
                        "ЧАСТЬ2: особенности (не должна появиться)"
                    ),
                }
            ],
            "extra": {"stop": ["STOPHERE", "\nSTOPHERE"]},
        },
        {
            "id": "json_schema",
            "title": "Строгая схема (response_format json_schema)",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"{base}\n\n"
                        "Верни только JSON-объект со полями summary, uses, features."
                    ),
                }
            ],
            "extra": {
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "python_overview",
                        "strict": True,
                        "schema": SCHEMA,
                    },
                }
            },
        },
    ]


def run_experiment(
    api_key: str,
    runs: int = RUNS,
    base_prompt: str | None = None,
    on_progress=None,
) -> dict:
    """Прогон всех вариантов. on_progress(variant_id, run_index, runs, row) — опционально."""
    runs = max(1, min(int(runs), 5))
    prompt = (base_prompt or "").strip() or BASE_PROMPT
    variants = build_variants(prompt)
    results: dict[str, list[dict]] = {}
    for variant in variants:
        vid = variant["id"]
        results[vid] = []
        for i in range(1, runs + 1):
            row = run_variant_once(api_key, variant)
            results[vid].append(row)
            if on_progress:
                on_progress(vid, i, runs, row)
            time.sleep(0.3)

    comparison = []
    for v in variants:
        rows = results[v["id"]]
        n = len(rows)
        comparison.append(
            {
                "id": v["id"],
                "title": v["title"],
                "extra": v["extra"],
                "api_ok": sum(1 for r in rows if r["ok"]),
                "json_parse": sum(1 for r in rows if r["json_parse_ok"]),
                "schema_ok": sum(1 for r in rows if r["schema_ok"]),
                "format_ok": sum(1 for r in rows if r["format_ok"]),
                "avg_chars": round(sum(r["chars"] for r in rows) / n, 1) if n else 0,
                "breaks": analyze_breaks(v["id"], rows),
                "runs": rows,
            }
        )

    return {
        "base_prompt": prompt,
        "model": MODEL,
        "api_url": API_URL,
        "runs": runs,
        "variants": [
            {
                "id": v["id"],
                "title": v["title"],
                "extra": v["extra"],
                "messages": v["messages"],
            }
            for v in variants
        ],
        "results": results,
        "comparison": comparison,
        "conclusions": conclusions(results),
        "report_markdown": build_report(results, runs, base_prompt=prompt, variants=variants),
    }


def save_artifacts(payload: dict) -> tuple[Path, Path]:
    dump_path = ROOT / "experiment_control_raw.json"
    report_path = ROOT / "experiment_control_report.md"
    dump_path.write_text(
        json.dumps(
            {
                "base_prompt": payload["base_prompt"],
                "model": payload["model"],
                "variants": payload["variants"],
                "results": payload["results"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    report_path.write_text(payload["report_markdown"], encoding="utf-8")
    return report_path, dump_path


def main() -> None:
    api_key = load_api_key()
    print(f"Model={MODEL}, runs={RUNS}")

    def on_progress(vid: str, i: int, runs: int, row: dict) -> None:
        title = next(v["title"] for v in build_variants(BASE_PROMPT) if v["id"] == vid)
        if i == 1:
            print(f"\n=== {title} ({vid}) ===")
        status = "OK" if row["ok"] else f"FAIL {(row.get('error') or '')[:80]}"
        print(f"  run {i}/{runs}... {status} chars={row['chars']} finish={row['finish_reason']}")

    payload = run_experiment(api_key, RUNS, base_prompt=BASE_PROMPT, on_progress=on_progress)
    report_path, dump_path = save_artifacts(payload)
    print(f"\nReport: {report_path}")
    print(f"Raw:    {dump_path}")


def build_report(
    results: dict[str, list[dict]],
    runs: int | None = None,
    base_prompt: str | None = None,
    variants: list[dict] | None = None,
) -> str:
    if runs is None:
        sample = next(iter(results.values()), [])
        runs = len(sample) if sample else RUNS
    prompt = base_prompt or BASE_PROMPT
    variants = variants or VARIANTS
    lines: list[str] = []
    lines.append("# Контроль ответа LLM: один запрос, разные ограничения")
    lines.append("")
    lines.append(f"- **API:** `{API_URL}`")
    lines.append(f"- **Модель:** `{MODEL}`")
    lines.append(f"- **Прогонов на вариант:** {runs}")
    lines.append("")
    lines.append("## Базовый запрос")
    lines.append("")
    lines.append("```")
    lines.append(prompt)
    lines.append("```")
    lines.append("")
    lines.append("## Варианты")
    lines.append("")
    lines.append("| ID | Что меняем |")
    lines.append("|---|---|")
    for v in variants:
        lines.append(f"| `{v['id']}` | {v['title']} |")
    lines.append("")

    for v in variants:
        vid = v["id"]
        rows = results[vid]
        n = len(rows) or runs
        lines.append(f"## {v['title']} (`{vid}`)")
        lines.append("")
        if v["extra"]:
            lines.append("Параметры запроса:")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(v["extra"], ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        else:
            lines.append("Дополнительных параметров API нет (только текст промпта).")
            lines.append("")

        ok_n = sum(1 for r in rows if r["ok"])
        json_n = sum(1 for r in rows if r["json_parse_ok"])
        schema_n = sum(1 for r in rows if r["schema_ok"])
        fmt_n = sum(1 for r in rows if r["format_ok"])
        avg_chars = round(sum(r["chars"] for r in rows) / len(rows), 1) if rows else 0
        lines.append(
            f"**Сводка:** успех API {ok_n}/{n}; "
            f"JSON parse {json_n}/{n}; "
            f"схема {schema_n}/{n}; "
            f"текстовый формат {fmt_n}/{n}; "
            f"средняя длина {avg_chars} символов."
        )
        lines.append("")

        for i, r in enumerate(rows, 1):
            lines.append(f"### Прогон {i}")
            lines.append("")
            if not r["ok"]:
                lines.append(f"- Ошибка: `{r['error']}`")
                lines.append("")
                continue
            lines.append(
                f"- finish_reason: `{r['finish_reason']}`; "
                f"chars: {r['chars']}; "
                f"model: `{r['model']}`; "
                f"время: {r['elapsed_sec']}s"
            )
            if r["usage"]:
                lines.append(f"- usage: `{json.dumps(r['usage'], ensure_ascii=False)}`")
            lines.append(
                f"- JSON parse: **{'да' if r['json_parse_ok'] else 'нет'}** "
                f"({r['json_parse_note']})"
            )
            lines.append(
                f"- Валидация схемы: **{'да' if r['schema_ok'] else 'нет'}** "
                f"({r['schema_note']})"
            )
            if vid == "format_prompt":
                lines.append(
                    f"- Текстовый формат: **{'да' if r['format_ok'] else 'нет'}** "
                    f"({r['format_note']})"
                )
            if vid == "stop":
                lines.append(
                    f"- Маркер STOPHERE в ответе: "
                    f"**{'да' if r['contains_stop_marker'] else 'нет'}**"
                )
            lines.append("")
            lines.append("<details><summary>Текст ответа</summary>")
            lines.append("")
            lines.append("```")
            lines.append(md_escape(r["content"] or ""))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    # comparison
    lines.append("## Сравнение")
    lines.append("")
    lines.append("| Вариант | API OK | Ср. длина | JSON parse | Схема | Что ломается |")
    lines.append("|---|---:|---:|---:|---:|---|")

    break_notes = {
        "baseline": analyze_breaks("baseline", results["baseline"]),
        "format_prompt": analyze_breaks("format_prompt", results["format_prompt"]),
        "max_tokens": analyze_breaks("max_tokens", results["max_tokens"]),
        "stop": analyze_breaks("stop", results["stop"]),
        "json_schema": analyze_breaks("json_schema", results["json_schema"]),
    }

    for v in variants:
        rows = results[v["id"]]
        n = len(rows) or runs
        ok_n = sum(1 for r in rows if r["ok"])
        json_n = sum(1 for r in rows if r["json_parse_ok"])
        schema_n = sum(1 for r in rows if r["schema_ok"])
        avg_chars = round(sum(r["chars"] for r in rows) / len(rows), 1) if rows else 0
        lines.append(
            f"| {v['title']} | {ok_n}/{n} | {avg_chars} | "
            f"{json_n}/{n} | {schema_n}/{n} | {break_notes[v['id']]} |"
        )

    lines.append("")
    lines.append("## Выводы")
    lines.append("")
    lines.extend(conclusions(results))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"Сырые данные: `experiment_control_raw.json`. Скрипт: `experiment_control.py`."
    )
    lines.append("")
    return "\n".join(lines)


def analyze_breaks(vid: str, rows: list[dict]) -> str:
    n = len(rows) or 1
    if not any(r["ok"] for r in rows):
        errs = [r["error"] for r in rows if r["error"]]
        sample = errs[0][:120].replace("|", "/") if errs else "ошибка API"
        return f"ломается на API: {sample}"
    if vid == "baseline":
        if not any(r["json_parse_ok"] for r in rows):
            return "свободный текст — парсинг JSON кодом не проходит"
        return "иногда JSON, чаще свободный текст"
    if vid == "format_prompt":
        fmt = sum(1 for r in rows if r["format_ok"])
        if fmt == n:
            return "формат держится, но это не машинная гарантия"
        if fmt == 0:
            return "ломается соблюдение текстового формата"
        return f"формат нестабилен ({fmt}/{n})"
    if vid == "max_tokens":
        truncated = sum(1 for r in rows if r["finish_reason"] == "length")
        if truncated:
            return f"обрезается по length ({truncated}/{n}), смысл неполный"
        short = sum(1 for r in rows if r["chars"] < 120)
        if short:
            return "ответ короткий/усечённый, полный смысл теряется"
        return "лимит почти не сработал"
    if vid == "stop":
        leaked = sum(1 for r in rows if r["contains_stop_marker"])
        if leaked:
            return "stop-маркер попал в ответ / stop не сработал жёстко"
        part2 = sum(1 for r in rows if "ЧАСТЬ2" in (r["content"] or ""))
        if part2:
            return "stop не отрезал генерацию до ЧАСТЬ2"
        if all(r["finish_reason"] == "stop" for r in rows if r["ok"]):
            return "stop сработал (finish_reason=stop)"
        return "поведение stop неоднозначно"
    if vid == "json_schema":
        if not any(r["ok"] for r in rows):
            return "API отвергает response_format / schema"
        schema_n = sum(1 for r in rows if r["schema_ok"])
        json_n = sum(1 for r in rows if r["json_parse_ok"])
        if schema_n == n:
            return "схема держится — парсинг стабилен"
        if json_n and schema_n < n:
            return "JSON есть, но схема соблюдается не всегда"
        if json_n == 0:
            return "ломается на валидном JSON / схема не enforced"
        return f"частично: schema {schema_n}/{n}"
    return "—"


def conclusions(results: dict[str, list[dict]]) -> list[str]:
    out: list[str] = []
    base = results["baseline"]
    fmt = results["format_prompt"]
    st = results["stop"]
    js = results["json_schema"]
    n = len(base) or 1

    out.append(
        "1. **Без ограничений** модель отвечает свободным текстом: человеку удобно, "
        f"машине нет — JSON parse {sum(1 for r in base if r['json_parse_ok'])}/{n}."
    )
    out.append(
        "2. **Явный формат в промпте** улучшает структуру, но это soft-constraint: "
        f"соблюдение шаблона {sum(1 for r in fmt if r['format_ok'])}/{n}, "
        "гарантии парсинга нет."
    )
    out.append(
        "3. **max_tokens** режет объём (часто `finish_reason=length`), "
        "из-за этого ответ обрывается на полуслове — ломается полнота смысла, "
        "не формат."
    )
    out.append(
        "4. **stop sequence** работает только если модель реально доходит до маркера; "
        "при игнорировании структуры промпта stop может не сработать как задумано. "
        f"Маркер в тексте: {sum(1 for r in st if r['contains_stop_marker'])}/{n}, "
        f"finish_reason=stop: {sum(1 for r in st if r['finish_reason']=='stop')}/{n}."
    )
    api_js = sum(1 for r in js if r["ok"])
    if api_js == 0:
        out.append(
            "5. **Строгая JSON Schema** на этом маршруте/модели **ломается на уровне API** "
            "(ошибка запроса или отсутствие поддержки `response_format`). "
            "Для машинного парсинга тогда остаётся промпт + клиентская валидация, "
            "либо другая модель с Structured Outputs."
        )
    else:
        out.append(
            "5. **Строгая JSON Schema** даёт лучший шанс на стабильный `json.loads` + "
            f"проверку полей: schema OK {sum(1 for r in js if r['schema_ok'])}/{n}, "
            f"JSON parse {sum(1 for r in js if r['json_parse_ok'])}/{n}. "
            "Если schema_ok < 100%, значит провайдер/модель не enforce'ит strict schema "
            "до конца — ломается гарантия структуры."
        )
    out.append(
        "6. **Практический вывод:** для кода надёжнее `response_format` + валидация схемы "
        "на клиенте; промпт-формат — хрупко; `max_tokens` и `stop` — про длину/обрезку, "
        "а не про структуру данных."
    )
    return out


if __name__ == "__main__":
    main()
