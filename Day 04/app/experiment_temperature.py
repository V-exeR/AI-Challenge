"""Day 04: temperature 0 / 0.7 / 1.2 × exact vs generation × 5 runs."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tasks import (
    TASKS,
    check_exact,
    check_generation,
    diversity_stats,
    task_user_text,
)

ROOT = Path(__file__).resolve().parent
API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
# agent/low иногда роутит на qwen с длинным hidden-reasoning → пустой content.
# По умолчанию фиксируем gemma; в UI можно вернуть agent/low.
DEFAULT_MODEL = "google/gemma4:31b"
MODEL_CHOICES = [
    {
        "id": "google/gemma4:31b",
        "label": "google/gemma4:31b (стабильнее для temp-эксперимента)",
    },
    {
        "id": "wormsoft/agent/low",
        "label": "wormsoft/agent/low (автороутинг, риск пустого content)",
    },
]
TIMEOUT_SEC = 180
MAX_TOKENS = 4096
MAX_429_RETRIES = 10
RATE_LIMIT_PAD_SEC = 2
EMPTY_CONTENT_RETRIES = 2
RUNS = 5
REASONING = {"effort": "none"}

TEMPERATURES = [0.0, 0.7, 1.2]


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
    raise ValueError("Нет WORMSOFT_API_KEY в окружении или .env")


def parse_retry_after_seconds(detail: str) -> int | None:
    if not detail:
        return None
    try:
        obj = json.loads(detail)
        detail = str(obj.get("message") or obj.get("error") or detail)
    except Exception:
        pass
    m = re.search(r"try again in\s+(\d+)\s*seconds?", detail, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*seconds?", detail, re.I)
    if m:
        return int(m.group(1))
    return None


def recover_text_from_reasoning(reasoning: str) -> str:
    """Если финальный content пуст, пробуем вытащить ответ из reasoning."""
    if not reasoning or not str(reasoning).strip():
        return ""
    text = str(reasoning)
    # Ищем нумерованный список из ≥5 пунктов
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*(?:\d+[\).\:\-]|[-*•])\s+(.+)$", line.strip())
        if m:
            items.append(m.group(1).strip())
    if len(items) >= 5:
        return "\n".join(f"{i}. {name}" for i, name in enumerate(items[:5], 1))
    # Ищем ANSWER:
    m = re.search(r"(?im)\bANSWER\s*:\s*(.+)\s*$", text)
    if m:
        return f"ANSWER: {m.group(1).strip()}"
    # Последний блок после маркеров вроде Final/Answer/Итог
    m = re.search(
        r"(?is)(?:final answer|итоговый ответ|итог|ответ)\s*[:\-]?\s*(.+)$",
        text,
    )
    if m:
        tail = m.group(1).strip()
        if tail:
            return tail[:2000]
    return ""


def chat(
    api_key: str,
    messages: list[dict],
    temperature: float,
    model: str,
    on_status=None,
) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": MAX_TOKENS,
        "temperature": temperature,
        "reasoning": REASONING,
        "reasoning_effort": "none",
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    t0 = time.time()

    for attempt in range(1, MAX_429_RETRIES + 1):
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
            elapsed = round(time.time() - t0, 2)
            choice = data["choices"][0]
            msg = choice.get("message") or {}
            content = msg.get("content")
            if content is None:
                content = ""
            reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
            usage = data.get("usage") or {}
            total_tokens = usage.get("total_tokens")
            if total_tokens is None:
                total_tokens = (usage.get("prompt_tokens") or 0) + (
                    usage.get("completion_tokens") or 0
                )
            return {
                "ok": True,
                "content": content,
                "reasoning": reasoning,
                "has_reasoning": bool(str(reasoning).strip()),
                "finish_reason": choice.get("finish_reason"),
                "model": data.get("model"),
                "usage": usage,
                "total_tokens": int(total_tokens or 0),
                "elapsed_sec": elapsed,
                "error": None,
            }
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < MAX_429_RETRIES:
                wait = (parse_retry_after_seconds(detail) or 60) + RATE_LIMIT_PAD_SEC
                msg = (
                    f"HTTP 429: лимит запросов. Ждём {wait} с "
                    f"(попытка {attempt}/{MAX_429_RETRIES})…"
                )
                print(msg)
                if on_status:
                    on_status({"type": "rate_limit", "wait_sec": wait, "message": msg})
                time.sleep(wait)
                continue
            return {
                "ok": False,
                "content": "",
                "reasoning": "",
                "has_reasoning": False,
                "finish_reason": None,
                "model": None,
                "usage": None,
                "total_tokens": 0,
                "elapsed_sec": round(time.time() - t0, 2),
                "error": f"HTTP {e.code}: {detail}",
            }
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "content": "",
                "reasoning": "",
                "has_reasoning": False,
                "finish_reason": None,
                "model": None,
                "usage": None,
                "total_tokens": 0,
                "elapsed_sec": round(time.time() - t0, 2),
                "error": str(e),
            }

    return {
        "ok": False,
        "content": "",
        "reasoning": "",
        "has_reasoning": False,
        "finish_reason": None,
        "model": None,
        "usage": None,
        "total_tokens": 0,
        "elapsed_sec": round(time.time() - t0, 2),
        "error": "HTTP 429: превышено число повторов после rate limit",
    }


def run_one(
    api_key: str,
    task: dict,
    temperature: float,
    run_index: int,
    model: str = DEFAULT_MODEL,
    on_status=None,
) -> dict:
    messages = [{"role": "user", "content": task_user_text(task)}]
    attempts: list[dict] = []
    out = None
    recovered_from_reasoning = False
    for attempt in range(1, EMPTY_CONTENT_RETRIES + 1):
        out = chat(api_key, messages, temperature, model=model, on_status=on_status)
        content = out.get("content") or ""
        reasoning = out.get("reasoning") or ""
        recovered = False
        if out.get("ok") and not content.strip() and reasoning.strip():
            recovered_text = recover_text_from_reasoning(reasoning)
            if recovered_text.strip():
                content = recovered_text
                out = {**out, "content": content}
                recovered = True
                recovered_from_reasoning = True
        attempts.append(
            {
                "attempt": attempt,
                "ok": out.get("ok"),
                "finish_reason": out.get("finish_reason"),
                "model": out.get("model"),
                "total_tokens": out.get("total_tokens"),
                "content_len": len(content),
                "has_reasoning": out.get("has_reasoning"),
                "recovered_from_reasoning": recovered,
                "error": out.get("error"),
            }
        )
        empty_truncated = (
            out.get("ok")
            and not content.strip()
            and out.get("finish_reason") == "length"
        )
        if not empty_truncated:
            break
        msg = (
            f"Пустой content при finish=length "
            f"(model={out.get('model')}, tokens={out.get('total_tokens')}). "
            f"Повтор {attempt}/{EMPTY_CONTENT_RETRIES}…"
        )
        print(msg)
        if on_status:
            on_status({"type": "retry_empty", "message": msg, "attempt": attempt})
        time.sleep(0.5)

    assert out is not None
    content = out.get("content") or ""
    if task["kind"] == "exact":
        check = check_exact(task, content)
    else:
        check = check_generation(content)

    empty_note = None
    if out.get("ok") and not content.strip():
        empty_note = (
            f"Пустой content (finish={out.get('finish_reason')}, "
            f"model={out.get('model')}, tokens={out.get('total_tokens')}, "
            f"reasoning_chars={len(out.get('reasoning') or '')}). "
            "Бюджет max_tokens ушёл в скрытое рассуждение. "
            "Попробуйте модель google/gemma4:31b."
        )

    return {
        "task_id": task["id"],
        "task_title": task["title"],
        "task_kind": task["kind"],
        "temperature": temperature,
        "run": run_index,
        "request_model": model,
        "ok": bool(out.get("ok")),
        "correct": check.get("correct"),
        "format_broken": bool(check.get("format_broken")),
        "format_ok": bool(check.get("format_ok")),
        "check": check,
        "signature": check.get("signature") or "",
        "content": content,
        "reasoning": out.get("reasoning") or "",
        "has_reasoning": bool(out.get("has_reasoning")),
        "recovered_from_reasoning": recovered_from_reasoning,
        "empty_note": empty_note,
        "model": out.get("model"),
        "total_tokens": out.get("total_tokens") or 0,
        "elapsed_sec": out.get("elapsed_sec") or 0,
        "error": out.get("error") or empty_note,
        "finish_reason": out.get("finish_reason"),
        "attempts": attempts,
    }


def summarize_cell(runs: list[dict], task: dict, temperature: float) -> dict:
    ok_runs = [r for r in runs if r.get("ok")]
    sigs = [r.get("signature") or "" for r in ok_runs]
    texts = [r.get("content") or "" for r in ok_runs]
    div = diversity_stats(sigs, texts)

    format_broken = sum(1 for r in runs if r.get("format_broken"))
    api_fail = sum(1 for r in runs if not r.get("ok"))

    row = {
        "task_id": task["id"],
        "task_title": task["title"],
        "task_kind": task["kind"],
        "temperature": temperature,
        "runs": len(runs),
        "api_ok": len(ok_runs),
        "api_fail": api_fail,
        "format_broken": format_broken,
        "unique_count": div["unique_count"],
        "all_identical": div["all_identical"],
        "avg_pairwise_jaccard": div["avg_pairwise_jaccard"],
        "total_tokens": sum(r.get("total_tokens") or 0 for r in runs),
        "elapsed_sec": round(sum(r.get("elapsed_sec") or 0 for r in runs), 2),
    }

    if task["kind"] == "exact":
        correct = sum(1 for r in runs if r.get("correct"))
        wrong = sum(1 for r in runs if r.get("ok") and r.get("correct") is False)
        row["correct"] = correct
        row["wrong"] = wrong
        row["accuracy"] = round(correct / len(runs), 3) if runs else 0
    else:
        row["correct"] = None
        row["wrong"] = None
        row["accuracy"] = None
        row["format_ok_count"] = sum(1 for r in runs if r.get("format_ok"))

    return row


def build_conclusions(summary: list[dict], cells: list[dict]) -> list[str]:
    lines: list[str] = []

    def cell(task_id: str, temp: float) -> dict:
        return next(
            s for s in summary if s["task_id"] == task_id and s["temperature"] == temp
        )

    exact0 = cell("trucks", 0.0)
    exact07 = cell("trucks", 0.7)
    exact12 = cell("trucks", 1.2)
    gen0 = cell("names", 0.0)
    gen07 = cell("names", 0.7)
    gen12 = cell("names", 1.2)

    lines.append(
        f"Задача с одним ответом: верных из 5 — "
        f"t=0 → {exact0['correct']}, t=0.7 → {exact07['correct']}, t=1.2 → {exact12['correct']}; "
        f"сломан формат — {exact0['format_broken']}/{exact07['format_broken']}/{exact12['format_broken']}."
    )
    lines.append(
        f"Уникальность ответов (exact): "
        f"t=0 → {exact0['unique_count']}/5"
        f"{' (все одинаковые)' if exact0['all_identical'] else ''}, "
        f"t=0.7 → {exact07['unique_count']}/5, "
        f"t=1.2 → {exact12['unique_count']}/5."
    )

    if exact0["all_identical"] and exact0["correct"] == RUNS:
        lines.append(
            "temperature = 0 на этой модели/маршруте дал стабильно один и тот же верный ответ "
            "во всех 5 прогонах."
        )
    elif exact0["all_identical"]:
        lines.append(
            "temperature = 0 дал одинаковый ответ каждый раз, но он не всегда / не был верным."
        )
    else:
        lines.append(
            "temperature = 0 НЕ дал полностью одинаковый ответ каждый раз "
            f"(уникальных сигнатур: {exact0['unique_count']}/5) — детерминизм не гарантирован."
        )

    lines.append(
        f"Генерация названий: уникальных текстов "
        f"t=0 → {gen0['unique_count']}/5, t=0.7 → {gen07['unique_count']}/5, "
        f"t=1.2 → {gen12['unique_count']}/5; "
        f"средняя Jaccard-схожесть пар "
        f"{gen0['avg_pairwise_jaccard']}/{gen07['avg_pairwise_jaccard']}/{gen12['avg_pairwise_jaccard']}; "
        f"сломан формат списка — {gen0['format_broken']}/{gen07['format_broken']}/{gen12['format_broken']}."
    )

    lines.append(
        "Где разнообразие полезно: задача на генерацию (названия) — выше temperature обычно "
        "даёт больше разных вариантов. Где вредит: задача с одним правильным ответом — "
        "рост temperature повышает шанс уйти от эталона и/или сломать формат ANSWER."
    )
    lines.append(
        "Практическая рекомендация: для фактов/расчётов/извлечения — temperature ≈ 0; "
        "для умеренно творческих текстов — 0.7; для максимального разброса идей — 1.2 "
        "(с контролем формата на клиенте)."
    )
    return lines


def build_report(payload: dict) -> str:
    lines = [
        "# Day 04 — температура",
        "",
        f"- **Модель:** `{payload['model']}`",
        f"- **API:** `{payload['api_url']}`",
        "- **Reasoning:** `effort=none`",
        f"- **Temperatures:** {', '.join(str(t) for t in TEMPERATURES)}",
        f"- **Прогонов на комбинацию:** {RUNS}",
        "",
        "## Задачи",
        "",
    ]
    for t in payload["tasks"]:
        ans = t["answer"] if t["answer"] is not None else "—"
        lines.append(f"- `{t['id']}` ({t['kind']}): {t['title']} — эталон `{ans}`")
    lines += ["", "## Сводная таблица", ""]
    lines.append(
        "| Задача | temp | Верных | Формат сломан | Уникальных | Jaccard | Токены | Время, с |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in payload["summary"]:
        corr = (
            f"{r['correct']}/{r['runs']}" if r["correct"] is not None else "—"
        )
        jac = r["avg_pairwise_jaccard"] if r["avg_pairwise_jaccard"] is not None else "—"
        lines.append(
            f"| {r['task_title']} | {r['temperature']} | {corr} | "
            f"{r['format_broken']}/{r['runs']} | {r['unique_count']}/{r['runs']} | "
            f"{jac} | {r['total_tokens']} | {r['elapsed_sec']} |"
        )
    lines += ["", "## Выводы", ""]
    for c in payload["conclusions"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def run_experiment(api_key: str, model: str | None = None, on_event=None) -> dict:
    model = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    cells: list[dict] = []
    total = len(TEMPERATURES) * len(TASKS) * RUNS
    done = 0

    def emit(ev: dict) -> None:
        if on_event:
            on_event(ev)

    for temperature in TEMPERATURES:
        for task in TASKS:
            for run_i in range(1, RUNS + 1):
                done += 1
                emit(
                    {
                        "type": "progress",
                        "done": done,
                        "total": total,
                        "message": (
                            f"[{done}/{total}] model={model} temp={temperature} × "
                            f"{task['title']} × run {run_i}/{RUNS}"
                        ),
                        "temperature": temperature,
                        "task_id": task["id"],
                        "run": run_i,
                    }
                )
                cell = run_one(
                    api_key,
                    task,
                    temperature,
                    run_i,
                    model=model,
                    on_status=emit,
                )
                cells.append(cell)

                # partial summary for this task×temp so far
                group = [
                    c
                    for c in cells
                    if c["task_id"] == task["id"] and c["temperature"] == temperature
                ]
                partial_summary = [
                    summarize_cell(
                        [
                            c
                            for c in cells
                            if c["task_id"] == t["id"] and c["temperature"] == temp
                        ],
                        t,
                        temp,
                    )
                    for temp in TEMPERATURES
                    for t in TASKS
                    if any(
                        c["task_id"] == t["id"] and c["temperature"] == temp
                        for c in cells
                    )
                ]
                emit(
                    {
                        "type": "cell",
                        "done": done,
                        "total": total,
                        "cell": cell,
                        "summary": partial_summary,
                        "group_size": len(group),
                    }
                )
                time.sleep(0.25)

    summary = [
        summarize_cell(
            [
                c
                for c in cells
                if c["task_id"] == t["id"] and c["temperature"] == temp
            ],
            t,
            temp,
        )
        for temp in TEMPERATURES
        for t in TASKS
    ]
    conclusions = build_conclusions(summary, cells)
    payload = {
        "model": model,
        "api_url": API_URL,
        "temperatures": TEMPERATURES,
        "runs": RUNS,
        "tasks": [
            {
                "id": t["id"],
                "kind": t["kind"],
                "title": t["title"],
                "prompt": t["prompt"],
                "answer": t["answer"],
            }
            for t in TASKS
        ],
        "cells": cells,
        "summary": summary,
        "conclusions": conclusions,
    }
    payload["report_markdown"] = build_report(payload)
    emit({"type": "done", "result": payload})
    return payload


def save_artifacts(payload: dict) -> tuple[Path, Path]:
    raw_path = ROOT / "experiment_raw.json"
    report_path = ROOT / "experiment_report.md"
    dump = {k: v for k, v in payload.items() if k != "report_markdown"}
    raw_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(payload["report_markdown"], encoding="utf-8")
    return report_path, raw_path


def main() -> None:
    api_key = load_api_key()

    def on_event(ev: dict) -> None:
        t = ev.get("type")
        if t in {"progress", "rate_limit"}:
            print(ev.get("message") or "")
        elif t == "cell":
            c = ev["cell"]
            if c["task_kind"] == "exact":
                mark = "OK" if c.get("correct") else "FAIL"
            else:
                mark = "FMT_OK" if c.get("format_ok") else "FMT_BAD"
            print(
                f"  -> {mark} temp={c['temperature']} run={c['run']} "
                f"sig={str(c.get('signature'))[:60]!r}"
            )

    print(f"Model={DEFAULT_MODEL}, temps={TEMPERATURES}, runs={RUNS}")
    payload = run_experiment(api_key, model=DEFAULT_MODEL, on_event=on_event)
    report_path, raw_path = save_artifacts(payload)
    print("\nSummary:")
    for r in payload["summary"]:
        print(
            f"  {r['task_id']:8} t={r['temperature']:<4} "
            f"correct={r.get('correct')} uniq={r['unique_count']} "
            f"fmt_broken={r['format_broken']} tokens={r['total_tokens']}"
        )
    print(f"\nReport: {report_path}")
    print(f"Raw:    {raw_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(e, file=sys.stderr)
        sys.exit(1)
