# Day 02 — контроль формата ответа

Один и тот же запрос к LLM с разным уровнем контроля:

1. без ограничений  
2. явное описание формата в промпте  
3. `max_tokens`  
4. stop sequence  
5. строгая схема (`response_format` / JSON Schema)

Каждый вариант прогоняется несколько раз; ответы сравниваются, проверяется парсинг кодом.

## Состав

| Файл | Назначение |
|---|---|
| `experiment_control.py` | Скрипт прогонов и сборки отчёта |
| `experiment_control_report.md` | Итоговый отчёт |
| `experiment_control_raw.json` | Сырые ответы API |

## Запуск

```powershell
cd "Day 02/app"
copy .env.example .env   # вписать WORMSOFT_API_KEY
python experiment_control.py
```

Отчёт перезапишется в `experiment_control_report.md`.

## Вывод эксперимента

На `wormsoft/agent/low` строгий `json_schema` не гарантирует соответствие схеме — для кода нужна клиентская валидация. Подробности в отчёте.
