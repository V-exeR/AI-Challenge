# Day 05 — версии моделей

Одни и те же 6 задач (набор Day 03) на трёх тирах:

| Тир | Кандидаты (первый доступный) |
|---|---|
| small | `wormsoft/agent/low` → `openai/gpt-oss:20b` |
| medium | `wormsoft/agent/medium` → `openai/gpt-oss:120b` |
| flagship | `wormsoft/agent/high` → `google/gemma4:31b` → `anthropic/claude-haiku-4.5` |

Параметры: `temperature=0`, `reasoning.effort=none`, **1 прогон** на задачу.

Метрики: верность, время, токены, стоимость по ставкам `/models`
(`tokens/1e6 * rate` в условных единицах каталога Wormsoft).

## Запуск web

```powershell
cd "Day 05/app"
python server.py
```

http://127.0.0.1:8005

## CLI

```powershell
cd "Day 05/app"
copy .env.example .env
python experiment_models.py
```
