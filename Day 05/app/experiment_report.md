# Day 05 — версии моделей

- **API:** `https://ai.wormsoft.ru/api/gpt/chat/completions`
- **temperature:** `0.0`, **reasoning:** `none`
- **Прогонов на задачу:** 1
- **Стоимость:** единицы каталога Wormsoft (`tokens/1e6 * rate` из `/models`)

## Модели

- **Маленькая / дешёвая** (`small`): `wormsoft/agent/low` (returned `gemma4:31b-cloud`); fallback notes: —
- **Средняя** (`medium`): `wormsoft/agent/medium` (returned `gemma4:31b-cloud`); fallback notes: —
- **Флагман** (`flagship`): `google/gemma4:31b` (returned `gemma4:31b-cloud`); fallback notes: wormsoft/agent/high: HTTP 403: {"statusCode":403,"message":"Model wormsoft/agent/high is not available for your subscription","timestamp":"2026-11-08T09:40:10.961Z"}

## Задачи

- `binary_search` (algorithmic): Бинарный поиск — `4`
- `cars_meet` (analytical): Встреча автомобилей — `2`
- `syllogism` (logical): Силлогизм — `нет`
- `linear_search` (algorithmic): Линейный поиск — `100`
- `price` (analytical): Цена со скидкой и наценкой — `180`
- `boxes` (logical): Коробки с этикетками — `яблоки и груши`

## Сводная таблица

| Модель | Тир | Верных | Время, с | Токены | Стоимость (усл.) |
|---|---|---:|---:|---:|---:|
| `wormsoft/agent/low` | small | 6/6 | 30.02 | 2846 | 12.4772 |
| `wormsoft/agent/medium` | medium | 6/6 | 60.42 | 3480 | 2272.5 |
| `google/gemma4:31b` | flagship | 6/6 | 6.84 | 1595 | 227.86 |

## Выводы

- Точность: small 6/6, medium 6/6, flagship 6/6.
- Флагман дороже маленькой модели примерно в 18.26× по стоимости каталога (227.86 vs 12.4772 усл. ед.) и точнее на 0 задач(и).
- Скорость: small 30.02s суммарно, medium 60.42s, flagship 6.84s (флагман быстрее/сопоставим маленькой).
- Маленькой модели уже достаточно на: Бинарный поиск, Коробки с этикетками, Встреча автомобилей, Линейный поиск, Цена со скидкой и наценкой, Силлогизм.
- На этом наборе флагман не дал прироста точности относительно small — для похожих школьных/логических задач достаточно дешёвой модели.
- Зафиксированные модели: small=`wormsoft/agent/low`, medium=`wormsoft/agent/medium`, flagship=`google/gemma4:31b`.
