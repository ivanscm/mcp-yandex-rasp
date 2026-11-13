# mcp-yandex-rasp — MCP сервер для API Яндекс Расписаний

[Model Context Protocol](https://modelcontextprotocol.io) сервер, предоставляющий данные о маршрутах из [API Яндекс Расписаний](https://yandex.ru/dev/rasp/doc/ru/) AI-агентам (Claude Desktop, Cline, Cursor и др.).

## Возможности

- **Поиск маршрутов** — рейсы между станциями/городами: время, цены, перевозчики
- **Расписание станций** — отправления и прибытия по любой станции
- **Маршрут нитки** — все промежуточные остановки с расписанием
- **Ближайшие станции** — поиск по географическим координатам
- **Поиск станций** — по названию с кешированием справочника

## Получение API ключа

1. Перейдите в [Кабинет разработчика](https://developer.tech.yandex.ru)
2. Создайте ключ для сервиса «API Яндекс Расписаний»
3. Активируйте ключ по ссылке из письма

## Требования

- Python 3.10+
- Версия пакета `mcp-yandex-rasp` 0.2.0+ (MCP Python SDK 2.x, `mcp>=2,<3`)
- [uv](https://docs.astral.sh/uv/) (рекомендуется) или pip

## Быстрый старт

```bash
git clone https://github.com/ivanscm/mcp-yandex-rasp.git
cd mcp-yandex-rasp

cp .env.example .env
# Отредактируйте .env, укажите YANDEX_RASP_API_KEY

# Установка зависимостей (MCP SDK 2.x)
uv sync

# Запуск (stdio — для Claude Desktop, Cline, Cursor)
uv run server.py

# Или HTTP режим
uv run server.py --http --port 8082
```

## Инструменты

| Инструмент | Описание |
|---|---|
| `search_routes(from, to, date, transport_types, transfers)` | Поиск рейсов между станциями |
| `get_station_schedule(station, date, transport_types, event)` | Расписание по станции |
| `get_thread_stops(uid, date)` | Остановки нитки (маршрута) |
| `find_nearest_stations(lat, lng, distance, transport_types)` | Станции рядом с координатами |
| `find_nearest_city(lat, lng, distance)` | Ближайший город |
| `get_carrier_info(code, system)` | Информация о перевозчике |
| `search_stations(query, limit)` | Поиск станций по названию |
| `update_stations_cache()` | Обновление кеша станций |
| `get_copyright()` | Копирайт (обязателен к отображению) |

## Промпты

| Промпт | Описание |
|---|---|
| `plan_trip(from_city, to_city, date)` | Шаблон для планирования поездки |

## Конфигурация

### Claude Desktop

```json
{
  "mcpServers": {
    "ya-rasp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-yandex-rasp", "server.py"],
      "env": {
        "YANDEX_RASP_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Разработка

```bash
uv sync --extra dev
uv run pytest -v
```

С pip вместо uv:

```bash
pip install -e ".[dev]"
pytest -v
```

## Лицензия

MIT
