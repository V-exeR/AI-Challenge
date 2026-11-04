# Lesson 01 — минимальный запрос к LLM

Отправка одного запроса в LLM через API, получение ответа и вывод в CLI или простой web-интерфейс.

## Состав

| Файл | Назначение |
|---|---|
| `llm_chat.py` | CLI: ключ вручную → запрос → ответ в консоль |
| `server.py` | Локальный сервер: раздаёт `web/` и проксирует `/api/chat` |
| `web/` | HTML + CSS + JS интерфейс |

## Запуск CLI

```powershell
cd "Lesson 01/app"
python llm_chat.py Что такое Python?
```

## Запуск web

```powershell
cd "Lesson 01/app"
python server.py
```

Откройте http://127.0.0.1:8000 — введите API key и сообщение.

## Ключ

Скопируйте `.env.example` → `.env` и впишите ключ, либо введите его при запуске CLI / в форме web.
