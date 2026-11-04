"""Day 03: 4 способа промптинга × 2 режима reasoning на наборе задач."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tasks import TASKS, check_answer, task_user_text  # noqa: F401 — TASKS used by server

ROOT = Path(__file__).resolve().parent
API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
MODEL = "wormsoft/agent/low"
TIMEOUT_SEC = 180
MAX_TOKENS = 2048
MAX_429_RETRIES = 10
RATE_LIMIT_PAD_SEC = 2

REASONING_MODES = [
    {"id": "none", "title": "Минимальное рассуждение", "param": {"effort": "none"}},
    {"id": "high", "title": "Максимальное рассуждение", "param": {"effort": "high"}},
]

STRATEGIES = [
    {"id": "direct", "title": "Прямой ответ"},
    {"id": "step_by_step", "title": "Решай пошагово"},
    {"id": "meta_prompt", "title": "Сначала промпт, потом решение"},
    {"id": "experts", "title": "Группа экспертов"},
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
    raise ValueError("Нет WORMSOFT_API_KEY в окружении или .env")


def parse_retry_after_seconds(detail: str) -> int | None:
    """Достаёт N из 'Try again in N seconds' (и похожих формулировок)."""
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


def _fail_result(t0: float, error: str) -> dict:
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
        "error": error,
    }


def chat(
    api_key: str,
    messages: list[dict],
    reasoning_effort: str,
    on_status=None,
) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": reasoning_effort},
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
            content = msg.get("content") or ""
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
                wait = parse_retry_after_seconds(detail) or 60
                wait += RATE_LIMIT_PAD_SEC
                msg = (
                    f"HTTP 429: лимит запросов. Ждём {wait} с "
                    f"(попытка {attempt}/{MAX_429_RETRIES})…"
                )
                print(msg)
                if on_status:
                    on_status({"type": "rate_limit", "wait_sec": wait, "message": msg})
                time.sleep(wait)
                continue
            return _fail_result(t0, f"HTTP {e.code}: {detail}")
        except Exception as e:  # noqa: BLE001
            return _fail_result(t0, str(e))

    return _fail_result(t0, "HTTP 429: превышено число повторов после rate limit")


def build_messages(strategy_id: str, task: dict, crafted_prompt: str | None = None) -> list[dict]:
    base = task_user_text(task)
    if strategy_id == "direct":
        return [{"role": "user", "content": base}]
    if strategy_id == "step_by_step":
        return [
            {
                "role": "user",
                "content": (
                    f"{base}\n\n"
                    "Инструкция: решай пошагово. Сначала разбери условие, "
                    "затем выполни рассуждение по шагам, и только потом дай ANSWER."
                ),
            }
        ]
    if strategy_id == "meta_prompt":
        assert crafted_prompt is not None
        return [
            {
                "role": "user",
                "content": (
                    f"Ниже дан промпт для решения задачи. Следуй ему.\n\n"
                    f"--- ПРОМПТ ---\n{crafted_prompt}\n--- КОНЕЦ ПРОМПТА ---\n\n"
                    f"Задача:\n{base}"
                ),
            }
        ]
    if strategy_id == "experts":
        return [
            {
                "role": "user",
                "content": (
                    f"{base}\n\n"
                    "Решай задачу как группа экспертов:\n"
                    "1) Аналитик — формулирует условие и ключевые факты.\n"
                    "2) Инженер — предлагает решение и вычисления/логику.\n"
                    "3) Критик — ищет ошибки и утверждает или исправляет ответ.\n"
                    "Покажи краткий вклад каждого, затем согласованный итог в ANSWER."
                ),
            }
        ]
    raise ValueError(f"unknown strategy: {strategy_id}")


def meta_craft_prompt(
    api_key: str, task: dict, reasoning_effort: str, on_status=None
) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                "Составь короткий, чёткий промпт (на русском), который поможет другой модели "
                "правильно решить следующую задачу. Верни только текст промпта, без решения самой задачи.\n\n"
                f"Задача:\n{task['prompt']}"
            ),
        }
    ]
    return chat(api_key, messages, reasoning_effort, on_status=on_status)


def run_one(
    api_key: str,
    task: dict,
    strategy_id: str,
    reasoning_effort: str,
    on_status=None,
) -> dict:
    calls: list[dict] = []
    crafted = None
    if strategy_id == "meta_prompt":
        craft = meta_craft_prompt(api_key, task, reasoning_effort, on_status=on_status)
        calls.append({"stage": "craft_prompt", **craft})
        crafted = craft.get("content") or ""
        if not craft.get("ok"):
            return {
                "task_id": task["id"],
                "task_title": task["title"],
                "task_kind": task["kind"],
                "expected": task["answer"],
                "strategy": strategy_id,
                "reasoning": reasoning_effort,
                "ok": False,
                "correct": False,
                "check": check_answer(task, ""),
                "content": "",
                "reasoning_text": "",
                "has_reasoning": False,
                "total_tokens": craft.get("total_tokens") or 0,
                "elapsed_sec": craft.get("elapsed_sec") or 0,
                "error": craft.get("error"),
                "calls": calls,
                "crafted_prompt": crafted,
            }

    messages = build_messages(strategy_id, task, crafted_prompt=crafted)
    out = chat(api_key, messages, reasoning_effort, on_status=on_status)
    calls.append({"stage": "solve", **out})

    content = out.get("content") or ""
    check = check_answer(task, content)
    total_tokens = sum(c.get("total_tokens") or 0 for c in calls)
    elapsed = round(sum(c.get("elapsed_sec") or 0 for c in calls), 2)
    return {
        "task_id": task["id"],
        "task_title": task["title"],
        "task_kind": task["kind"],
        "expected": task["answer"],
        "strategy": strategy_id,
        "reasoning": reasoning_effort,
        "ok": bool(out.get("ok")),
        "correct": bool(check["ok"]) if out.get("ok") else False,
        "check": check,
        "content": content,
        "reasoning_text": out.get("reasoning") or "",
        "has_reasoning": bool(out.get("has_reasoning")),
        "finish_reason": out.get("finish_reason"),
        "model": out.get("model"),
        "total_tokens": total_tokens,
        "elapsed_sec": elapsed,
        "error": out.get("error"),
        "calls": [
            {
                "stage": c.get("stage"),
                "ok": c.get("ok"),
                "total_tokens": c.get("total_tokens"),
                "elapsed_sec": c.get("elapsed_sec"),
                "error": c.get("error"),
                "content_preview": (c.get("content") or "")[:240],
            }
            for c in calls
        ],
        "crafted_prompt": crafted,
    }


def summarize(cells: list[dict]) -> list[dict]:
    """Агрегация: strategy × reasoning."""
    rows = []
    for s in STRATEGIES:
        for r in REASONING_MODES:
            subset = [
                c
                for c in cells
                if c["strategy"] == s["id"] and c["reasoning"] == r["id"]
            ]
            rows.append(
                {
                    "strategy": s["id"],
                    "strategy_title": s["title"],
                    "reasoning": r["id"],
                    "reasoning_title": r["title"],
                    "correct": sum(1 for c in subset if c.get("correct")),
                    "total_tasks": len(subset),
                    "api_ok": sum(1 for c in subset if c.get("ok")),
                    "total_tokens": sum(c.get("total_tokens") or 0 for c in subset),
                    "elapsed_sec": round(sum(c.get("elapsed_sec") or 0 for c in subset), 2),
                    "with_reasoning": sum(1 for c in subset if c.get("has_reasoning")),
                }
            )
    return rows


def build_conclusions(summary: list[dict]) -> list[str]:
    by = {(r["strategy"], r["reasoning"]): r for r in summary}
    lines: list[str] = []

    def corr(sid: str, rid: str) -> int:
        return by[(sid, rid)]["correct"]

    def tok(sid: str, rid: str) -> int:
        return by[(sid, rid)]["total_tokens"]

    none_best = max(STRATEGIES, key=lambda s: corr(s["id"], "none"))
    high_best = max(STRATEGIES, key=lambda s: corr(s["id"], "high"))
    lines.append(
        f"При reasoning=none лучший способ по точности: «{none_best['title']}» "
        f"({corr(none_best['id'], 'none')}/6)."
    )
    lines.append(
        f"При reasoning=high лучший способ по точности: «{high_best['title']}» "
        f"({corr(high_best['id'], 'high')}/6)."
    )

    # which prompting gains vanish when reasoning is high
    gains = []
    for s in STRATEGIES:
        if s["id"] == "direct":
            continue
        gain_none = corr(s["id"], "none") - corr("direct", "none")
        gain_high = corr(s["id"], "high") - corr("direct", "high")
        gains.append((s["title"], gain_none, gain_high, tok(s["id"], "high")))

    vanished = [g for g in gains if g[1] > 0 and g[2] <= 0]
    if vanished:
        names = ", ".join(f"«{g[0]}»" for g in vanished)
        lines.append(
            f"Приёмы, которые давали прирост при выключенном рассуждении, "
            f"но перестали помогать при high: {names}."
        )
    else:
        lines.append(
            "Явного «обнуления» прироста промптинга при high не видно "
            "(или direct уже был силён / все способы близки)."
        )

    # cost note
    costly = max(STRATEGIES, key=lambda s: tok(s["id"], "high"))
    lines.append(
        f"Самый дорогой по токенам при high: «{costly['title']}» "
        f"({tok(costly['id'], 'high')} tokens). Meta-prompt обычно дороже из‑за двух вызовов."
    )
    lines.append(
        "Практический вывод: при включённом reasoning (effort=high) усложнение промпта "
        "часто даёт мало точности сверх direct/step-by-step, но увеличивает токены и время; "
        "выгоднее включать reasoning, чем городить экспертов, если задача уже «думающая»."
    )
    return lines


def build_report(payload: dict) -> str:
    lines: list[str] = []
    lines.append("# Day 03 — промптинг × рассуждение")
    lines.append("")
    lines.append(f"- **Модель:** `{payload['model']}`")
    lines.append(f"- **API:** `{payload['api_url']}`")
    lines.append("- **Reasoning min:** `effort=none`")
    lines.append("- **Reasoning max:** `effort=high`")
    lines.append(f"- **Задач:** {len(payload['tasks'])}")
    lines.append("")
    lines.append("## Задачи")
    lines.append("")
    for t in payload["tasks"]:
        lines.append(
            f"- `{t['id']}` ({t['kind']}): {t['title']} — эталон `{t['answer']}`"
        )
    lines.append("")
    lines.append("## Сводная таблица")
    lines.append("")
    lines.append("| Способ | Рассуждение | Верных | Токены | Время, с |")
    lines.append("|---|---|---:|---:|---:|")
    for r in payload["summary"]:
        lines.append(
            f"| {r['strategy_title']} | {r['reasoning']} | "
            f"{r['correct']}/{r['total_tasks']} | {r['total_tokens']} | {r['elapsed_sec']} |"
        )
    lines.append("")
    lines.append("## Выводы")
    lines.append("")
    for c in payload["conclusions"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def run_experiment(api_key: str, on_event=None) -> dict:
    """
    on_event(dict) — опциональные события для UI/CLI:
      {type: progress|rate_limit|cell|done, ...}
    """
    cells: list[dict] = []
    total = len(STRATEGIES) * len(REASONING_MODES) * len(TASKS)
    done = 0

    def emit(event: dict) -> None:
        if on_event:
            on_event(event)

    def on_status(ev: dict) -> None:
        emit(ev)

    for reasoning in REASONING_MODES:
        for strategy in STRATEGIES:
            for task in TASKS:
                done += 1
                emit(
                    {
                        "type": "progress",
                        "done": done,
                        "total": total,
                        "strategy": strategy["id"],
                        "strategy_title": strategy["title"],
                        "reasoning": reasoning["id"],
                        "task_id": task["id"],
                        "task_title": task["title"],
                        "message": (
                            f"[{done}/{total}] {strategy['title']} × "
                            f"{reasoning['id']} × {task['title']}"
                        ),
                    }
                )
                cell = run_one(
                    api_key,
                    task,
                    strategy["id"],
                    reasoning["id"],
                    on_status=on_status,
                )
                cells.append(cell)
                emit(
                    {
                        "type": "cell",
                        "done": done,
                        "total": total,
                        "cell": cell,
                        "summary": summarize(cells),
                    }
                )
                time.sleep(0.25)

    summary = summarize(cells)
    conclusions = build_conclusions(summary)
    payload = {
        "model": MODEL,
        "api_url": API_URL,
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
        "strategies": STRATEGIES,
        "reasoning_modes": REASONING_MODES,
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
    raw_path.write_text(
        json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_path.write_text(payload["report_markdown"], encoding="utf-8")
    return report_path, raw_path


def main() -> None:
    api_key = load_api_key()

    def on_event(ev: dict) -> None:
        t = ev.get("type")
        if t == "progress":
            print(ev.get("message") or "")
        elif t == "rate_limit":
            print(ev.get("message") or f"rate limit, wait {ev.get('wait_sec')}s")
        elif t == "cell":
            c = ev["cell"]
            mark = "OK" if c.get("correct") else "FAIL"
            print(
                f"  -> {mark} got={c.get('check', {}).get('normalized')} "
                f"expected={c.get('check', {}).get('expected')} "
                f"tokens={c.get('total_tokens')} {c.get('elapsed_sec')}s"
            )

    print(f"Model={MODEL}, tasks={len(TASKS)}")
    payload = run_experiment(api_key, on_event=on_event)
    report_path, raw_path = save_artifacts(payload)
    print("\nSummary:")
    for r in payload["summary"]:
        print(
            f"  {r['strategy']:12} {r['reasoning']:4}  "
            f"correct={r['correct']}/{r['total_tasks']}  "
            f"tokens={r['total_tokens']}  time={r['elapsed_sec']}s"
        )
    print(f"\nReport: {report_path}")
    print(f"Raw:    {raw_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(e, file=sys.stderr)
        sys.exit(1)
