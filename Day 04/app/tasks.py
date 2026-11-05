"""Задачи Day 04: один правильный ответ vs генерация."""

from __future__ import annotations

import re
from typing import Any

TASKS: list[dict[str, Any]] = [
    {
        "id": "trucks",
        "kind": "exact",
        "title": "Мешки и машины (один ответ)",
        "prompt": (
            "В одну машину влезает 50 мешков картошки. "
            "Сколько надо машин, чтобы увезти 320 мешков картошки?"
        ),
        "answer": "7",
        "answer_type": "number",
    },
    {
        "id": "names",
        "kind": "generation",
        "title": "Названия магазина сантехники (генерация)",
        "prompt": (
            "Придумай 5 названий для магазина сантехники. "
            "Выведи ТОЛЬКО нумерованный список 1–5, без вступлений и без рассуждений."
        ),
        "answer": None,
        "answer_type": "list5",
    },
]

ANSWER_INSTRUCTION = (
    "В конце ответа обязательно выведи одну строку вида:\n"
    "ANSWER: <число>\n"
    "Без лишнего текста после этой строки."
)


def task_user_text(task: dict[str, Any]) -> str:
    if task["kind"] == "exact":
        return f"{task['prompt']}\n\n{ANSWER_INSTRUCTION}"
    return task["prompt"]


def extract_answer(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"(?im)^\s*ANSWER\s*:\s*(.+?)\s*$", text)
    if m:
        return m.group(1).strip()
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else None


def _norm_number(s: str) -> str | None:
    s = s.strip().lower().replace(",", ".")
    s = re.sub(r"(машин[аыу]?|шт\.?|штук[аи]?)", "", s).strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    val = float(m.group(0))
    if val.is_integer():
        return str(int(val))
    return str(val).rstrip("0").rstrip(".")


def extract_list_items(text: str) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^(?:\d+[\).\:\-]|[-*•])\s*(.+)$", line)
        if m:
            items.append(m.group(1).strip().strip('"«»'))
    if len(items) >= 5:
        return items[:5]
    # fallback: split by semicolon/comma if single line
    if not items and text.strip():
        parts = re.split(r"[;\n]|,\s*", text.strip())
        items = [p.strip().strip('"«»') for p in parts if p.strip()]
    return items[:5]


def format_ok_generation(text: str) -> bool:
    return len(extract_list_items(text)) >= 5


def check_exact(task: dict[str, Any], model_text: str) -> dict[str, Any]:
    extracted = extract_answer(model_text)
    has_answer_line = bool(re.search(r"(?im)^\s*ANSWER\s*:", model_text or ""))
    got = _norm_number(extracted) if extracted else None
    expected = task["answer"]
    correct = got is not None and got == expected
    format_broken = not has_answer_line
    return {
        "extracted": extracted,
        "normalized": got,
        "expected": expected,
        "correct": correct,
        "format_broken": format_broken,
        "format_ok": not format_broken,
        "signature": got or (extracted or "").strip().lower(),
    }


def check_generation(model_text: str) -> dict[str, Any]:
    items = extract_list_items(model_text)
    fmt_ok = len(items) >= 5
    # signature for uniqueness: normalized joined names
    sig = " | ".join(re.sub(r"\s+", " ", x.lower()) for x in items[:5])
    return {
        "extracted": items,
        "normalized": sig,
        "expected": None,
        "correct": None,
        "format_broken": not fmt_ok,
        "format_ok": fmt_ok,
        "signature": sig,
        "items": items,
    }


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-яё0-9]+", (text or "").lower().replace("ё", "е")))


def pairwise_jaccard(texts: list[str]) -> float | None:
    """Средняя Jaccard-схожесть по всем парам (1 = одинаковые, 0 = разные)."""
    n = len(texts)
    if n < 2:
        return None
    total = 0.0
    pairs = 0
    for i in range(n):
        ti = tokenize(texts[i])
        for j in range(i + 1, n):
            tj = tokenize(texts[j])
            if not ti and not tj:
                sim = 1.0
            else:
                inter = len(ti & tj)
                union = len(ti | tj) or 1
                sim = inter / union
            total += sim
            pairs += 1
    return round(total / pairs, 3) if pairs else None


def diversity_stats(signatures: list[str], full_texts: list[str]) -> dict[str, Any]:
    uniq = len(set(signatures))
    return {
        "unique_count": uniq,
        "runs": len(signatures),
        "all_identical": uniq == 1 and len(signatures) > 0,
        "avg_pairwise_jaccard": pairwise_jaccard(full_texts),
        "distinct_pair_ratio": round(
            1 - (pairwise_jaccard(full_texts) or 0), 3
        )
        if len(full_texts) >= 2
        else None,
    }
