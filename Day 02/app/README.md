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
| `web/` | HTML/CSS/JS интерфейс эксперимента |
| `server.py` | Локальный сервер (порт **8001**) |
| `experiment_control.py` | Логика прогонов (CLI и API) |
| `experiment_control_report.md` | Итоговый отчёт |
| `experiment_control_raw.json` | Сырые ответы API |

## Запуск через web

```powershell
cd "Day 02/app"
python server.py
```

Откройте http://127.0.0.1:8001 — введите API key, число прогонов и нажмите «Запустить эксперимент».
На странице появятся таблица сравнения, тексты ответов и выводы. Отчёт также сохранится в `experiment_control_report.md`.

## Запуск через CLI

```powershell
cd "Day 02/app"
copy .env.example .env   # вписать WORMSOFT_API_KEY
python experiment_control.py
```

## Вывод эксперимента

На `wormsoft/agent/low` строгий `json_schema` не гарантирует соответствие схеме — для кода нужна клиентская валидация. Подробности в отчёте / на web-странице.
