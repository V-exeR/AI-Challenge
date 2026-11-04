"""Задачи Day 03: логические, алгоритмические, аналитические."""

from __future__ import annotations

import re
from typing import Any

TASKS: list[dict[str, Any]] = [
    {
        "id": "binary_search",
        "kind": "algorithmic",
        "title": "Бинарный поиск",
        "prompt": (
            "Дан отсортированный массив из 16 различных элементов. "
            "Сколько сравнений с элементами массива потребуется бинарному поиску "
            "в худшем случае, чтобы найти целевой элемент (или установить, что его нет)? "
            "Считай классический вариант: на каждом шаге одно сравнение с серединой, "
            "затем выбор половины."
        ),
        # В разных учебниках худший случай для n=16 считают как 4 или 5.
        "answer": "4",
        "accepted_answers": ["4", "5"],
        "answer_type": "number",
    },
    {
        "id": "cars_meet",
        "kind": "analytical",
        "title": "Встреча автомобилей",
        "prompt": (
            "Из пункта А в пункт Б выехал автомобиль со скоростью 60 км/ч. "
            "Одновременно из пункта Б в пункт А выехал другой автомобиль со скоростью 80 км/ч. "
            "Расстояние между А и Б — 280 км. Автомобили едут навстречу друг другу "
            "по одной дороге без остановок. Через сколько часов они встретятся?"
        ),
        "answer": "2",
        "answer_type": "number",
        "accept_units": True,
    },
    {
        "id": "syllogism",
        "kind": "logical",
        "title": "Силлогизм",
        "prompt": (
            "Дано: (1) Все блюдца — чашки. (2) Некоторые чашки — тарелки. "
            "Следует ли из этого, что некоторые блюдца — тарелки? "
            "Ответь «да» или «нет»."
        ),
        "answer": "нет",
        "answer_type": "yesno",
    },
    {
        "id": "linear_search",
        "kind": "algorithmic",
        "title": "Линейный поиск",
        "prompt": (
            "Массив из 100 элементов просматривается линейным поиском слева направо. "
            "Сколько сравнений с элементами массива будет в худшем случае "
            "(искомого элемента нет или он последний)?"
        ),
        "answer": "100",
        "answer_type": "number",
    },
    {
        "id": "price",
        "kind": "analytical",
        "title": "Цена со скидкой и наценкой",
        "prompt": (
            "Товар стоил 200 рублей. Сначала сделали скидку 25%, "
            "затем на получившуюся цену наценили 20%. "
            "Какова итоговая цена в рублях?"
        ),
        "answer": "180",
        "answer_type": "number",
    },
    {
        "id": "boxes",
        "kind": "logical",
        "title": "Коробки с этикетками",
        "prompt": (
            "Есть три коробки. На них этикетки: «яблоки», «груши», «яблоки и груши». "
            "Известно, что ВСЕ этикетки врут (ни одна не соответствует содержимому). "
            "Открыли коробку с этикеткой «яблоки и груши» — внутри только яблоки. "
            "Что лежит в коробке с этикеткой «груши»? "
            "Ответь одной из фраз: «яблоки», «груши» или «яблоки и груши»."
        ),
        "answer": "яблоки и груши",
        "answer_type": "text",
    },
]

ANSWER_INSTRUCTION = (
    "В конце ответа обязательно выведи одну строку вида:\n"
    "ANSWER: <итоговое значение>\n"
    "Без лишнего текста после этой строки."
)


def task_user_text(task: dict[str, Any]) -> str:
    return f"{task['prompt']}\n\n{ANSWER_INSTRUCTION}"


def extract_answer(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"(?im)^\s*ANSWER\s*:\s*(.+?)\s*$", text)
    if m:
        return m.group(1).strip()
    # fallback: last non-empty line
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else None


def _norm_yesno(s: str) -> str:
    s = s.strip().lower().replace("ё", "е")
    s = re.sub(r"[.!?]+$", "", s)
    if s in {"да", "yes", "true", "y"}:
        return "да"
    if s in {"нет", "no", "false", "n"}:
        return "нет"
    return s


def _norm_number(s: str) -> str | None:
    s = s.strip().lower().replace(",", ".")
    s = re.sub(r"(часа|часов|час|ч|руб(?:лей|ля)?|₽)", "", s).strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    val = float(m.group(0))
    if val.is_integer():
        return str(int(val))
    return str(val).rstrip("0").rstrip(".") if "." in str(val) else str(val)


def _norm_boxes(s: str) -> str:
    s = s.strip().lower().replace("ё", "е")
    s = re.sub(r"[.!?]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    if "яблок" in s and "груш" in s:
        return "яблоки и груши"
    if "яблок" in s:
        return "яблоки"
    if "груш" in s:
        return "груши"
    return s


def normalize_for_task(task: dict[str, Any], raw: str | None) -> str | None:
    if raw is None:
        return None
    t = task.get("answer_type")
    if t == "yesno":
        return _norm_yesno(raw)
    if t == "number":
        return _norm_number(raw)
    if task["id"] == "boxes":
        return _norm_boxes(raw)
    return re.sub(r"\s+", " ", raw.strip().lower().replace("ё", "е"))


def check_answer(task: dict[str, Any], model_text: str) -> dict[str, Any]:
    extracted = extract_answer(model_text)
    got = normalize_for_task(task, extracted)
    expected = normalize_for_task(task, task["answer"])
    accepted = task.get("accepted_answers")
    if accepted:
        accepted_norm = [normalize_for_task(task, a) for a in accepted]
        ok = got is not None and got in accepted_norm
        expected_display = "/".join(str(a) for a in accepted)
    else:
        ok = got is not None and expected is not None and got == expected
        expected_display = expected
    return {
        "extracted": extracted,
        "normalized": got,
        "expected": expected_display,
        "ok": ok,
    }
