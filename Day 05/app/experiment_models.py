"""Day 05: сравнение small / medium / flagship моделей на задачах Day 03."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tasks import TASKS, check_answer, task_user_text

ROOT = Path(__file__).resolve().parent
API_URL = "https://ai.wormsoft.ru/api/gpt/chat/completions"
MODELS_URL = "https://ai.wormsoft.ru/api/gpt/models"
TIMEOUT_SEC = 180
MAX_TOKENS = 2048
MAX_429_RETRIES = 10
RATE_LIMIT_PAD_SEC = 2
TEMPERATURE = 0.0
REASONING = {"effort": "none"}

# Тиры: маленькая / средняя / флагман (с запасными id при 403)
MODEL_TIERS = [
    {
        "tier": "small",
        "title": "Маленькая / дешёвая",
        "candidates": ["wormsoft/agent/low", "openai/gpt-oss:20b"],
    },
    {
        "tier": "medium",
        "title": "Средняя",
        "candidates": ["wormsoft/agent/medium", "openai/gpt-oss:120b"],
    },
    {
        "tier": "flagship",
        "title": "Флагман",
        "candidates": [
            "wormsoft/agent/high",
            "google/gemma4:31b",
            "anthropic/claude-haiku-4.5",
        ],
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


def fetch_pricing(api_key: str) -> dict[str, dict]:
    """id -> {prompt, completion} цены из /models (за 1M токенов в единицах каталога)."""
    req = urllib.request.Request(
        MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    out: dict[str, dict] = {}
    for m in data.get("data") or []:
        mid = m.get("id")
        pricing = m.get("pricing") or {}
        if not mid:
            continue
        try:
            out[mid] = {
                "prompt": float(pricing.get("prompt") or 0),
                "completion": float(pricing.get("completion") or 0),
                "raw": pricing,
            }
        except (TypeError, ValueError):
            out[mid] = {"prompt": 0.0, "completion": 0.0, "raw": pricing}
    return out


def estimate_cost(usage: dict | None, rates: dict | None) -> float | None:
    if not usage or not rates:
        return None
    pt = float(usage.get("prompt_tokens") or 0)
    ct = float(usage.get("completion_tokens") or 0)
    # Каталог Wormsoft: ставка за 1M токенов → cost = tokens/1e6 * rate
    return round(
        (pt / 1_000_000.0) * float(rates.get("prompt") or 0)
        + (ct / 1_000_000.0) * float(rates.get("completion") or 0),
        6,
    )


def chat(
    api_key: str,
    model: str,
    messages: list[dict],
    on_status=None,
) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
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
            content = msg.get("content") or ""
            usage = data.get("usage") or {}
            total_tokens = usage.get("total_tokens")
            if total_tokens is None:
                total_tokens = (usage.get("prompt_tokens") or 0) + (
                    usage.get("completion_tokens") or 0
                )
            return {
                "ok": True,
                "content": content,
                "finish_reason": choice.get("finish_reason"),
                "model_returned": data.get("model"),
                "usage": usage,
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": int(total_tokens or 0),
                "elapsed_sec": elapsed,
                "http_status": 200,
                "error": None,
            }
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < MAX_429_RETRIES:
                wait = (parse_retry_after_seconds(detail) or 60) + RATE_LIMIT_PAD_SEC
                msg = (
                    f"HTTP 429: ждём {wait} с "
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
                "finish_reason": None,
                "model_returned": None,
                "usage": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "elapsed_sec": round(time.time() - t0, 2),
                "http_status": e.code,
                "error": f"HTTP {e.code}: {detail}",
            }
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "content": "",
                "finish_reason": None,
                "model_returned": None,
                "usage": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "elapsed_sec": round(time.time() - t0, 2),
                "http_status": 0,
                "error": str(e),
            }

    return {
        "ok": False,
        "content": "",
        "finish_reason": None,
        "model_returned": None,
        "usage": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "elapsed_sec": round(time.time() - t0, 2),
        "http_status": 429,
        "error": "HTTP 429: превышено число повторов",
    }


def resolve_models(api_key: str, on_status=None) -> list[dict]:
    """Пробует candidates по тиру; при 403/недоступности берёт следующий."""
    resolved = []
    probe_messages = [
        {
            "role": "user",
            "content": "Ответь одним словом: ok\n\nANSWER: ok",
        }
    ]
    for tier in MODEL_TIERS:
        chosen = None
        notes = []
        for cand in tier["candidates"]:
            if on_status:
                on_status(
                    {
                        "type": "progress",
                        "message": f"Проверка модели {cand} (tier={tier['tier']})…",
                    }
                )
            out = chat(api_key, cand, probe_messages, on_status=on_status)
            if out.get("ok"):
                chosen = {
                    "tier": tier["tier"],
                    "title": tier["title"],
                    "model_id": cand,
                    "model_returned": out.get("model_returned"),
                    "probe_tokens": out.get("total_tokens"),
                    "fallback_notes": notes,
                }
                break
            notes.append(f"{cand}: {out.get('error') or out.get('http_status')}")
            # 403/404 — сразу следующий кандидат
            if out.get("http_status") not in {403, 404, 400} and not out.get("ok"):
                # сетевые сбои — тоже пробуем следующего
                pass
        if not chosen:
            chosen = {
                "tier": tier["tier"],
                "title": tier["title"],
                "model_id": None,
                "model_returned": None,
                "probe_tokens": 0,
                "fallback_notes": notes,
                "error": "Нет доступной модели в тире",
            }
        resolved.append(chosen)
        time.sleep(0.3)
    return resolved


def run_one(
    api_key: str,
    task: dict,
    model_info: dict,
    pricing: dict[str, dict],
    on_status=None,
) -> dict:
    model_id = model_info.get("model_id")
    if not model_id:
        return {
            "task_id": task["id"],
            "task_title": task["title"],
            "task_kind": task["kind"],
            "tier": model_info["tier"],
            "tier_title": model_info["title"],
            "model_id": None,
            "ok": False,
            "correct": False,
            "check": check_answer(task, ""),
            "content": "",
            "error": model_info.get("error") or "model unavailable",
            "elapsed_sec": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost": None,
        }

    messages = [{"role": "user", "content": task_user_text(task)}]
    out = chat(api_key, model_id, messages, on_status=on_status)
    content = out.get("content") or ""
    check = check_answer(task, content)
    rates = pricing.get(model_id)
    cost = estimate_cost(out.get("usage"), rates)

    return {
        "task_id": task["id"],
        "task_title": task["title"],
        "task_kind": task["kind"],
        "expected": task["answer"],
        "tier": model_info["tier"],
        "tier_title": model_info["title"],
        "model_id": model_id,
        "model_returned": out.get("model_returned"),
        "ok": bool(out.get("ok")),
        "correct": bool(check.get("ok")) if out.get("ok") else False,
        "check": check,
        "content": content,
        "finish_reason": out.get("finish_reason"),
        "elapsed_sec": out.get("elapsed_sec") or 0,
        "prompt_tokens": out.get("prompt_tokens") or 0,
        "completion_tokens": out.get("completion_tokens") or 0,
        "total_tokens": out.get("total_tokens") or 0,
        "cost": cost,
        "rates": rates,
        "error": out.get("error"),
    }


def summarize(cells: list[dict], models: list[dict]) -> list[dict]:
    rows = []
    for m in models:
        subset = [c for c in cells if c.get("tier") == m["tier"]]
        n = len(subset)
        correct = sum(1 for c in subset if c.get("correct"))
        rows.append(
            {
                "tier": m["tier"],
                "tier_title": m["title"],
                "model_id": m.get("model_id"),
                "model_returned": m.get("model_returned"),
                "fallback_notes": m.get("fallback_notes") or [],
                "correct": correct,
                "total_tasks": n,
                "accuracy": round(correct / n, 3) if n else 0,
                "elapsed_sec": round(sum(c.get("elapsed_sec") or 0 for c in subset), 2),
                "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in subset),
                "completion_tokens": sum(c.get("completion_tokens") or 0 for c in subset),
                "total_tokens": sum(c.get("total_tokens") or 0 for c in subset),
                "cost": round(
                    sum(c.get("cost") or 0 for c in subset if c.get("cost") is not None),
                    6,
                ),
                "api_ok": sum(1 for c in subset if c.get("ok")),
            }
        )
    return rows


def build_conclusions(summary: list[dict], cells: list[dict]) -> list[str]:
    by_tier = {r["tier"]: r for r in summary}
    small = by_tier.get("small") or {}
    medium = by_tier.get("medium") or {}
    flag = by_tier.get("flagship") or {}
    lines = []

    lines.append(
        f"Точность: small {small.get('correct', 0)}/{small.get('total_tasks', 0)}, "
        f"medium {medium.get('correct', 0)}/{medium.get('total_tasks', 0)}, "
        f"flagship {flag.get('correct', 0)}/{flag.get('total_tasks', 0)}."
    )

    s_cost = float(small.get("cost") or 0) or None
    f_cost = float(flag.get("cost") or 0) or None
    if s_cost and f_cost and s_cost > 0:
        ratio = round(f_cost / s_cost, 2)
        delta_acc = (flag.get("correct") or 0) - (small.get("correct") or 0)
        lines.append(
            f"Флагман дороже маленькой модели примерно в {ratio}× по стоимости каталога "
            f"({f_cost} vs {s_cost} усл. ед.) и точнее на {delta_acc} задач(и)."
        )
    else:
        lines.append(
            "Сравнение стоимости incomplete (нет pricing или нулевая стоимость в каталоге)."
        )

    s_t = float(small.get("elapsed_sec") or 0) or None
    f_t = float(flag.get("elapsed_sec") or 0) or None
    if s_t and f_t:
        lines.append(
            f"Скорость: small {s_t}s суммарно, medium {medium.get('elapsed_sec')}s, "
            f"flagship {f_t}s "
            f"(флагман {'медленнее' if f_t > s_t else 'быстрее/сопоставим'} маленькой)."
        )

    # задачи, где small уже справился
    small_ok = {
        c["task_id"]
        for c in cells
        if c.get("tier") == "small" and c.get("correct")
    }
    flag_only = {
        c["task_id"]
        for c in cells
        if c.get("tier") == "flagship" and c.get("correct") and c["task_id"] not in small_ok
    }
    if small_ok:
        titles = {
            c["task_id"]: c["task_title"]
            for c in cells
            if c.get("tier") == "small"
        }
        names = ", ".join(titles[t] for t in sorted(small_ok))
        lines.append(f"Маленькой модели уже достаточно на: {names}.")
    if flag_only:
        titles = {c["task_id"]: c["task_title"] for c in cells}
        names = ", ".join(titles[t] for t in sorted(flag_only) if t in titles)
        lines.append(f"Флагман выигрывает там, где small ошибся: {names}.")
    if not flag_only and small.get("correct") == flag.get("correct"):
        lines.append(
            "На этом наборе флагман не дал прироста точности относительно small — "
            "для похожих школьных/логических задач достаточно дешёвой модели."
        )

    lines.append(
        f"Зафиксированные модели: small=`{small.get('model_id')}`, "
        f"medium=`{medium.get('model_id')}`, flagship=`{flag.get('model_id')}`."
    )
    return lines


def build_report(payload: dict) -> str:
    lines = [
        "# Day 05 — версии моделей",
        "",
        f"- **API:** `{payload['api_url']}`",
        f"- **temperature:** `{TEMPERATURE}`, **reasoning:** `none`",
        f"- **Прогонов на задачу:** 1",
        f"- **Стоимость:** единицы каталога Wormsoft (`tokens/1e6 * rate` из `/models`)",
        "",
        "## Модели",
        "",
    ]
    for m in payload["models"]:
        notes = "; ".join(m.get("fallback_notes") or []) or "—"
        lines.append(
            f"- **{m['title']}** (`{m['tier']}`): `{m.get('model_id')}` "
            f"(returned `{m.get('model_returned')}`); fallback notes: {notes}"
        )
    lines += ["", "## Задачи", ""]
    for t in payload["tasks"]:
        lines.append(f"- `{t['id']}` ({t['kind']}): {t['title']} — `{t['answer']}`")
    lines += [
        "",
        "## Сводная таблица",
        "",
        "| Модель | Тир | Верных | Время, с | Токены | Стоимость (усл.) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in payload["summary"]:
        lines.append(
            f"| `{r.get('model_id')}` | {r['tier']} | "
            f"{r['correct']}/{r['total_tasks']} | {r['elapsed_sec']} | "
            f"{r['total_tokens']} | {r['cost']} |"
        )
    lines += ["", "## Выводы", ""]
    for c in payload["conclusions"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def run_experiment(api_key: str, on_event=None) -> dict:
    def emit(ev: dict) -> None:
        if on_event:
            on_event(ev)

    emit({"type": "progress", "message": "Загрузка цен из /models…"})
    pricing = fetch_pricing(api_key)
    emit({"type": "progress", "message": "Резолв моделей по тирам (probe)…"})
    models = resolve_models(api_key, on_status=emit)

    cells: list[dict] = []
    total = len(models) * len(TASKS)
    done = 0
    for m in models:
        for task in TASKS:
            done += 1
            emit(
                {
                    "type": "progress",
                    "done": done,
                    "total": total,
                    "message": (
                        f"[{done}/{total}] {m['tier']} `{m.get('model_id')}` × {task['title']}"
                    ),
                }
            )
            cell = run_one(api_key, task, m, pricing, on_status=emit)
            cells.append(cell)
            emit(
                {
                    "type": "cell",
                    "done": done,
                    "total": total,
                    "cell": cell,
                    "summary": summarize(cells, models),
                }
            )
            time.sleep(0.3)

    summary = summarize(cells, models)
    conclusions = build_conclusions(summary, cells)
    payload = {
        "api_url": API_URL,
        "temperature": TEMPERATURE,
        "models": models,
        "pricing_note": "cost = prompt_tokens/1e6*prompt_rate + completion_tokens/1e6*completion_rate",
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
            mark = "OK" if c.get("correct") else "FAIL"
            print(
                f"  -> {mark} {c.get('tier')} {c.get('task_id')} "
                f"tokens={c.get('total_tokens')} cost={c.get('cost')} "
                f"{c.get('elapsed_sec')}s"
            )

    payload = run_experiment(api_key, on_event=on_event)
    report_path, raw_path = save_artifacts(payload)
    print("\nSummary:")
    for r in payload["summary"]:
        print(
            f"  {r['tier']:8} {r.get('model_id')}  "
            f"correct={r['correct']}/{r['total_tasks']}  "
            f"time={r['elapsed_sec']}s  tokens={r['total_tokens']}  cost={r['cost']}"
        )
    print(f"\nReport: {report_path}")
    print(f"Raw:    {raw_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(e, file=sys.stderr)
        sys.exit(1)
