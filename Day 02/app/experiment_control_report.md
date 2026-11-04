# Контроль ответа LLM: один запрос, разные ограничения

- **API:** `https://ai.wormsoft.ru/api/gpt/chat/completions`
- **Модель:** `wormsoft/agent/low`
- **Прогонов на вариант:** 3

## Базовый запрос

```
Опиши вкратце язык программирования Rust: что это, для чего используют, и назови ровно три ключевые особенности.
```

## Варианты

| ID | Что меняем |
|---|---|
| `baseline` | Без ограничений |
| `format_prompt` | Явное описание формата в промпте |
| `max_tokens` | Ограничение объёма (max_tokens=40) |
| `stop` | Stop sequence |
| `json_schema` | Строгая схема (response_format json_schema) |

## Без ограничений (`baseline`)

Дополнительных параметров API нет (только текст промпта).

**Сводка:** успех API 3/3; JSON parse 0/3; схема 0/3; текстовый формат 0/3; средняя длина 829.7 символов.

### Прогон 1

- finish_reason: `stop`; chars: 936; model: `gemma4:31b-cloud`; время: 2.67s
- usage: `{"prompt_tokens": 43, "completion_tokens": 231, "total_tokens": 274, "prompt_tokens_details": {"cached_tokens": 0}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный системный язык программирования, созданный для обеспечения максимальной производительности и безопасности памяти без использования сборщика мусора (garbage collector).

**Для чего используют:**
*   Разработка операционных систем, драйверов и браузеров.
*   Создание высоконагруженных серверных приложений (бэкенд).
*   Разработка игровых движков и систем реального времени.
*   Создание инструментов для WebAssembly (Wasm).

**Три ключевые особенности:**
1.  **Безопасность памяти (Ownership & Borrowing):** уникальная система владения и заимствования, которая исключает ошибки сегментации и утечки памяти на этапе компиляции.
2.  **Отсутствие сборщика мусора:** управление ресурсами происходит статически, что дает скорость работы, сравнимую с C и C++.
3.  **Безопасная многопоточность:** строгие правила компилятора предотвращают «состояние гонки» (data races), делая параллельное программирование надежным.
```

</details>

### Прогон 2

- finish_reason: `stop`; chars: 912; model: `gemma4:31b-cloud`; время: 2.21s
- usage: `{"prompt_tokens": 43, "completion_tokens": 213, "total_tokens": 256, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный системный язык программирования, который обеспечивает высокую производительность и гарантирует безопасность работы с памятью без использования сборщика мусора (garbage collector).

**Для чего используют:**
Его применяют там, где важна скорость и надежность: разработка операционных систем, браузеров, высоконагруженных серверных сервисов, игровых движков и приложений для встроенных систем (embedded).

**Три ключевые особенности:**
1. **Безопасность памяти (Ownership):** уникальная система владения и заимствования, которая исключает ошибки сегментации и утечки памяти на этапе компиляции.
2. **Отсутствие сборщика мусора:** позволяет достичь производительности на уровне C и C++, обеспечивая предсказуемое управление ресурсами.
3. **Безопасная многопоточность:** строгие правила компилятора предотвращают «состояние гонки» (data races), делая параллельное программирование надежным.
```

</details>

### Прогон 3

- finish_reason: `stop`; chars: 641; model: `gemma4:31b-cloud`; время: 1.81s
- usage: `{"prompt_tokens": 43, "completion_tokens": 169, "total_tokens": 212, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный компилируемый язык системного программирования, разработанный для обеспечения максимальной производительности и безопасности памяти.

**Для чего используют:**
Его применяют там, где важна скорость и надежность: создание операционных систем, браузеров, игровых движков, высоконагруженных бэкендов и приложений для блокчейна (WebAssembly).

**Три ключевые особенности:**
1. **Безопасность памяти без сборщика мусора** (благодаря системе владения и заимствования).
2. **Отсутствие «состояний гонки»** (гарантированная потокобезопасность при многопоточности).
3. **Высокая производительность**, сопоставимая с C и C++.
```

</details>

## Явное описание формата в промпте (`format_prompt`)

Дополнительных параметров API нет (только текст промпта).

**Сводка:** успех API 3/3; JSON parse 0/3; схема 0/3; текстовый формат 3/3; средняя длина 322.7 символов.

### Прогон 1

- finish_reason: `stop`; chars: 348; model: `gemma4:31b-cloud`; время: 1.24s
- usage: `{"prompt_tokens": 104, "completion_tokens": 88, "total_tokens": 192, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Текстовый формат: **да** (формат SUMMARY/USES/FEATURES соблюдён)

<details><summary>Текст ответа</summary>

```
SUMMARY: Современный системный язык программирования, обеспечивающий высокую производительность и безопасность памяти.
USES: Системное ПО, веб-сервисы, разработка движков, блокчейн, встроенные системы
FEATURES:
1. Система владения и заимствования
2. Отсутствие сборщика мусора
3. Строгая статическая типизация и проверка безопасности в compile-time
```

</details>

### Прогон 2

- finish_reason: `stop`; chars: 322; model: `gemma4:31b-cloud`; время: 1.24s
- usage: `{"prompt_tokens": 104, "completion_tokens": 89, "total_tokens": 193, "prompt_tokens_details": {"cached_tokens": 96}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Текстовый формат: **да** (формат SUMMARY/USES/FEATURES соблюдён)

<details><summary>Текст ответа</summary>

```
SUMMARY: Системный язык программирования, обеспечивающий высокую производительность и безопасность работы с памятью.
USES: системное программирование, веб-сервисы, разработка движков, блокчейн
FEATURES:
1. Владение и заимствование (Ownership & Borrowing)
2. Отсутствие сборщика мусора
3. Гарантированная потокобезопасность
```

</details>

### Прогон 3

- finish_reason: `stop`; chars: 298; model: `gemma4:31b-cloud`; время: 1.34s
- usage: `{"prompt_tokens": 104, "completion_tokens": 81, "total_tokens": 185, "prompt_tokens_details": {"cached_tokens": 96}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Текстовый формат: **да** (формат SUMMARY/USES/FEATURES соблюдён)

<details><summary>Текст ответа</summary>

```
SUMMARY: Системный язык программирования, обеспечивающий высокую производительность и безопасность памяти.
USES: системное ПО, веб-сервисы, блокчейн, игровые движки, встроенные системы
FEATURES:
1. Система владения и заимствования
2. Отсутствие сборщика мусора
3. Гарантированная потокобезопасность
```

</details>

## Ограничение объёма (max_tokens=40) (`max_tokens`)

Параметры запроса:

```json
{
  "max_tokens": 40
}
```

**Сводка:** успех API 3/3; JSON parse 0/3; схема 0/3; текстовый формат 0/3; средняя длина 190.7 символов.

### Прогон 1

- finish_reason: `length`; chars: 186; model: `gemma4:31b-cloud`; время: 1.16s
- usage: `{"prompt_tokens": 43, "completion_tokens": 40, "total_tokens": 83, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный системный язык программирования, который сочетает в себе высокую производительность C++ и гарантии безопасности памяти.

**Для чего используют:**
Его применяют
```

</details>

### Прогон 2

- finish_reason: `length`; chars: 191; model: `gemma4:31b-cloud`; время: 0.93s
- usage: `{"prompt_tokens": 43, "completion_tokens": 40, "total_tokens": 83, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный системный язык программирования, который сочетает в себе высокую производительность C++ с гарантированной безопасностью работы с памятью.

**Для чего используют:**

```

</details>

### Прогон 3

- finish_reason: `length`; chars: 195; model: `gemma4:31b-cloud`; время: 0.83s
- usage: `{"prompt_tokens": 43, "completion_tokens": 40, "total_tokens": 83, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)

<details><summary>Текст ответа</summary>

```
**Rust** — это современный системный язык программирования, ориентированный на безопасность, скорость и параллелизм. Он призван стать безопасной альтернативой C++, позволяя писать высокопроизводи
```

</details>

## Stop sequence (`stop`)

Параметры запроса:

```json
{
  "stop": [
    "STOPHERE",
    "\nSTOPHERE"
  ]
}
```

**Сводка:** успех API 3/3; JSON parse 0/3; схема 0/3; текстовый формат 0/3; средняя длина 269.3 символов.

### Прогон 1

- finish_reason: `stop`; chars: 263; model: `gemma4:31b-cloud`; время: 0.92s
- usage: `{"prompt_tokens": 75, "completion_tokens": 58, "total_tokens": 133, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Маркер STOPHERE в ответе: **нет**

<details><summary>Текст ответа</summary>

```
Rust — это современный компилируемый язык программирования общего назначения, ориентированный на безопасность, скорость и параллелизм. Его используют для создания системного ПО, высоконагруженных сервисов, браузеров, игровых движков и разработки на WebAssembly.


```

</details>

### Прогон 2

- finish_reason: `stop`; chars: 282; model: `gemma4:31b-cloud`; время: 1.21s
- usage: `{"prompt_tokens": 75, "completion_tokens": 63, "total_tokens": 138, "prompt_tokens_details": {"cached_tokens": 64}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Маркер STOPHERE в ответе: **нет**

<details><summary>Текст ответа</summary>

```
Rust — это современный компилируемый язык программирования общего назначения, ориентированный на безопасность, скорость и параллелизм. Его используют для системного программирования, разработки операционных систем, высоконагруженных бэкенд-сервисов, игровых движков и WebAssembly.


```

</details>

### Прогон 3

- finish_reason: `stop`; chars: 263; model: `gemma4:31b-cloud`; время: 1.11s
- usage: `{"prompt_tokens": 75, "completion_tokens": 58, "total_tokens": 133, "prompt_tokens_details": {"cached_tokens": 64}}`
- JSON parse: **нет** (JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Валидация схемы: **нет** (n/a)
- Маркер STOPHERE в ответе: **нет**

<details><summary>Текст ответа</summary>

```
Rust — это современный системный язык программирования, который обеспечивает высокую производительность и безопасность памяти. Его используют для создания операционных систем, игровых движков, высоконагруженных бэкендов и инструментов для веб-ассемблера (Wasm).


```

</details>

## Строгая схема (response_format json_schema) (`json_schema`)

Параметры запроса:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "python_overview",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "summary": {
            "type": "string",
            "description": "Краткое описание Python"
          },
          "uses": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "minItems": 1,
            "maxItems": 5,
            "description": "Области применения"
          },
          "features": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "minItems": 3,
            "maxItems": 3,
            "description": "Ровно три ключевые особенности"
          }
        },
        "required": [
          "summary",
          "uses",
          "features"
        ],
        "additionalProperties": false
      }
    }
  }
}
```

**Сводка:** успех API 3/3; JSON parse 3/3; схема 0/3; текстовый формат 0/3; средняя длина 494.3 символов.

### Прогон 1

- finish_reason: `stop`; chars: 484; model: `gemma4:31b-cloud`; время: 1.32s
- usage: `{"prompt_tokens": 61, "completion_tokens": 130, "total_tokens": 191, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **да** (json.loads OK)
- Валидация схемы: **нет** (uses не array[string])

<details><summary>Текст ответа</summary>

```
```json
{
  "summary": "Rust — это современный системный язык программирования, ориентированный на безопасность, скорость и параллелизм.",
  "uses": "Разработка операционных систем, игровых движков, высоконагруженных серверных приложений, браузеров и WebAssembly.",
  "features": [
    "Безопасность памяти без сборщика мусора (Ownership & Borrowing)",
    "Высокая производительность, сопоставимая с C++",
    "Строгая статическая типизация и мощная система проверки типов"
  ]
}
```
```

</details>

### Прогон 2

- finish_reason: `stop`; chars: 515; model: `gemma4:31b-cloud`; время: 1.17s
- usage: `{"prompt_tokens": 61, "completion_tokens": 141, "total_tokens": 202, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **да** (json.loads OK)
- Валидация схемы: **нет** (uses не array[string])

<details><summary>Текст ответа</summary>

```
```json
{
  "summary": "Rust — это современный системный язык программирования, обеспечивающий высокую производительность и безопасность работы с памятью без использования сборщика мусора.",
  "uses": "Разработка операционных систем, высоконагруженных бэкендов, браузеров, движков игр и WebAssembly-приложений.",
  "features": [
    "Система владения (Ownership) и заимствования",
    "Гарантированная потокобезопасность (отсутствие data races)",
    "Строгая статическая типизация с мощным выводом типов"
  ]
}
```
```

</details>

### Прогон 3

- finish_reason: `stop`; chars: 484; model: `gemma4:31b-cloud`; время: 1.14s
- usage: `{"prompt_tokens": 61, "completion_tokens": 130, "total_tokens": 191, "prompt_tokens_details": {"cached_tokens": 32}}`
- JSON parse: **да** (json.loads OK)
- Валидация схемы: **нет** (uses не array[string])

<details><summary>Текст ответа</summary>

```
```json
{
  "summary": "Rust — это современный системный язык программирования, ориентированный на безопасность, скорость и параллелизм.",
  "uses": "Разработка операционных систем, браузеров, высоконагруженных серверных приложений, игровых движков и WebAssembly.",
  "features": [
    "Безопасность памяти без сборщика мусора (Ownership & Borrowing)",
    "Высокая производительность, сопоставимая с C++",
    "Строгая статическая типизация и мощная система проверки типов"
  ]
}
```
```

</details>

## Сравнение

| Вариант | API OK | Ср. длина | JSON parse | Схема | Что ломается |
|---|---:|---:|---:|---:|---|
| Без ограничений | 3/3 | 829.7 | 0/3 | 0/3 | свободный текст — парсинг JSON кодом не проходит |
| Явное описание формата в промпте | 3/3 | 322.7 | 0/3 | 0/3 | формат держится, но это не машинная гарантия |
| Ограничение объёма (max_tokens=40) | 3/3 | 190.7 | 0/3 | 0/3 | обрезается по length (3/3), смысл неполный |
| Stop sequence | 3/3 | 269.3 | 0/3 | 0/3 | stop сработал (finish_reason=stop) |
| Строгая схема (response_format json_schema) | 3/3 | 494.3 | 3/3 | 0/3 | JSON есть, но схема соблюдается не всегда |

## Выводы

1. **Без ограничений** модель отвечает свободным текстом: человеку удобно, машине нет — JSON parse 0/3.
2. **Явный формат в промпте** улучшает структуру, но это soft-constraint: соблюдение шаблона 3/3, гарантии парсинга нет.
3. **max_tokens** режет объём (часто `finish_reason=length`), из-за этого ответ обрывается на полуслове — ломается полнота смысла, не формат.
4. **stop sequence** работает только если модель реально доходит до маркера; при игнорировании структуры промпта stop может не сработать как задумано. Маркер в тексте: 0/3, finish_reason=stop: 3/3.
5. **Строгая JSON Schema** даёт лучший шанс на стабильный `json.loads` + проверку полей: schema OK 0/3, JSON parse 3/3. Если schema_ok < 100%, значит провайдер/модель не enforce'ит strict schema до конца — ломается гарантия структуры.
6. **Практический вывод:** для кода надёжнее `response_format` + валидация схемы на клиенте; промпт-формат — хрупко; `max_tokens` и `stop` — про длину/обрезку, а не про структуру данных.

---

Сырые данные: `experiment_control_raw.json`. Скрипт: `experiment_control.py`.
