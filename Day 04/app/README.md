# Day 04 — температура

Сравнение `temperature = 0 / 0.7 / 1.2` на двух типах задач:

1. **Один правильный ответ** — мешки и машины (эталон `7`)
2. **Генерация** — 5 названий магазина сантехники

Каждая комбинация — **5 прогонов**. Reasoning: `effort=none`.

По умолчанию модель **`google/gemma4:31b`**: у `wormsoft/agent/low` бывает роут на qwen,
где весь `max_tokens` уходит в скрытое reasoning и `content` остаётся пустым.

## Метрики

- верность / сломанный формат `ANSWER:` (exact)
- число уникальных ответов из 5
- средняя попарная Jaccard-схожесть текстов (generation)
- токены и время

## Запуск web

```powershell
cd "Day 04/app"
python server.py
```

http://127.0.0.1:8004 — результаты появляются по ходу прогона; при HTTP 429 — пауза из ответа + 2 с.

## CLI

```powershell
cd "Day 04/app"
copy .env.example .env
python experiment_temperature.py
```
