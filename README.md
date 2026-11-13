# mcp-yandex-rasp — MCP server for Yandex Rasp API

[Model Context Protocol](https://modelcontextprotocol.io) server that provides transport route data from [Yandex Rasp API](https://yandex.ru/dev/rasp/doc/ru/) to AI agents (Claude Desktop, Cline, Cursor, etc.).

## Features

- **Route search** — find trips between stations/cities with times, duration, prices
- **Station schedules** — departures and arrivals at any station
- **Thread details** — full route with all intermediate stops
- **Nearest stations** — find stations by geographic coordinates
- **Station search** — find station codes by name (cached locally)

## Getting an API key

1. Go to [Yandex Developer Cabinet](https://developer.tech.yandex.ru)
2. Create a new key for "API Яндекс Расписаний"
3. Activate the key via email

## Requirements

- Python 3.10+
- Package version `mcp-yandex-rasp` 0.2.0+ (built on MCP Python SDK 2.x, `mcp>=2,<3`)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Quick start

```bash
git clone https://github.com/ivanscm/mcp-yandex-rasp.git
cd mcp-yandex-rasp

cp .env.example .env
# Edit .env and set your YANDEX_RASP_API_KEY

# Install dependencies (MCP SDK 2.x)
uv sync

# Run (stdio mode — for Claude Desktop, Cline, Cursor)
uv run server.py

# Or run in HTTP mode
uv run server.py --http --port 8082
```

## Tools

| Tool | Description |
|---|---|
| `search_routes(from, to, date, transport_types, transfers)` | Search routes between stations/cities |
| `get_station_schedule(station, date, transport_types, event)` | Schedule at a station |
| `get_thread_stops(uid, date)` | All stops along a thread/route |
| `find_nearest_stations(lat, lng, distance, transport_types)` | Stations near coordinates |
| `find_nearest_city(lat, lng, distance)` | Nearest city to coordinates |
| `get_carrier_info(code, system)` | Transport carrier info |
| `search_stations(query, limit)` | Search stations by name (cached) |
| `update_stations_cache()` | Force re-download stations reference |
| `get_copyright()` | Copyright attribution (required) |

## Prompts

| Prompt | Description |
|---|---|
| `plan_trip(from_city, to_city, date)` | Template for trip planning |

## Configuration examples

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

### Cline / Cursor

Same as Claude Desktop config.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

## Development

```bash
uv sync --extra dev
uv run pytest -v
```

With pip instead of uv:

```bash
pip install -e ".[dev]"
pytest -v
```

## License

MIT
