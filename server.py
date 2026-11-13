import os
import sys
import ssl
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv
import httpx
import certifi
from mcp.server.mcpserver import MCPServer

load_dotenv()

API_KEY = os.getenv("YANDEX_RASP_API_KEY")
BASE_URL = "https://api.rasp.yandex-net.ru/v3.0"
CACHE_DIR = Path.home() / ".cache" / "mcp-yandex-rasp"
CACHE_DB = CACHE_DIR / "stations.db"

_HTTP_CLIENT: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(certifi.where())
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        _HTTP_CLIENT = httpx.AsyncClient(verify=ctx, timeout=httpx.Timeout(30.0))
    return _HTTP_CLIENT


logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# mcp 2.x: "name" is still the first positional parameter, but transport
# options (json_response, port, ...) moved from the constructor to run().
mcp = MCPServer("ya-rasp", version="0.2.0")


async def _fetch(endpoint: str, params: dict | None = None, timeout: float | None = None) -> dict:
    if not API_KEY:
        raise ValueError(
            "YANDEX_RASP_API_KEY environment variable is not set. "
            "Get your key at https://developer.tech.yandex.ru"
        )
    if params is None:
        params = {}
    params["apikey"] = API_KEY

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    client = _get_client()
    resp = await client.get(url, params=params, timeout=httpx.Timeout(timeout) if timeout else None)
    resp.raise_for_status()
    return resp.json()


# ── Stations cache ──────────────────────────────────────────────────

def _cache_exists() -> bool:
    return CACHE_DB.exists()


async def _build_cache() -> None:
    log.info("Downloading stations list (~40MB, may take a minute)...")
    data = await _fetch("stations_list/", timeout=120.0)
    log.info("Building search cache...")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS stations (
        code TEXT PRIMARY KEY, title TEXT, station_type TEXT,
        transport_type TEXT, lat REAL, lng REAL,
        settlement TEXT, region TEXT, country TEXT
    )""")

    count = 0
    for country in data.get("countries", []):
        cname = country.get("title", "")
        for region in country.get("regions", []):
            rname = region.get("title", "")
            for settlement in region.get("settlements", []):
                sname = settlement.get("title", "")
                for station in settlement.get("stations", []):
                    codes = station.get("codes", {})
                    code = codes.get("yandex_code") or codes.get("esr_code", "")
                    if not code:
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO stations VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            code,
                            station.get("title", ""),
                            station.get("station_type", ""),
                            station.get("transport_type", ""),
                            station.get("latitude"),
                            station.get("longitude"),
                            sname,
                            rname,
                            cname,
                        ),
                    )
                    count += 1

    conn.commit()
    conn.close()
    log.info("Cached %d stations", count)


async def _ensure_cache() -> None:
    if not _cache_exists():
        await _build_cache()


# ── Tools ───────────────────────────────────────────────────────────

@mcp.tool()
async def search_routes(
    from_: str,
    to: str,
    date: str | None = None,
    transport_types: str | None = None,
    transfers: bool = False,
    system: str = "yandex",
    offset: int = 0,
    limit: int = 100,
    lang: str = "ru_RU",
) -> dict:
    """Search routes between stations or cities.

    Returns available trips with departure/arrival times, duration,
    carrier info, ticket prices, and transport type.
    Station codes can be found via search_stations().
    City codes follow the pattern: c<number> (e.g. c213 for Moscow).
    Station codes follow the pattern: s<number> (e.g. s9600213).
    """
    params = {
        "from": from_,
        "to": to,
        "system": system,
        "offset": offset,
        "limit": limit,
        "lang": lang,
    }
    if date:
        params["date"] = date
    if transport_types:
        params["transport_types"] = transport_types
    if transfers:
        params["transfers"] = "true"

    return await _fetch("search/", params)


@mcp.tool()
async def get_station_schedule(
    station: str,
    date: str | None = None,
    transport_types: str | None = None,
    event: str = "departure",
    direction: str | None = None,
    system: str = "yandex",
    lang: str = "ru_RU",
) -> dict:
    """Get schedule of departures/arrivals at a station.

    Returns all trips passing through the station with times,
    thread info, and operating days.
    """
    params = {
        "station": station,
        "event": event,
        "system": system,
        "lang": lang,
    }
    if date:
        params["date"] = date
    if transport_types:
        params["transport_types"] = transport_types
    if direction:
        params["direction"] = direction

    return await _fetch("schedule/", params)


@mcp.tool()
async def get_thread_stops(
    uid: str,
    date: str | None = None,
    lang: str = "ru_RU",
) -> dict:
    """Get all intermediate stops along a thread (route).

    Returns a full list of stations with arrival/departure times,
    platform info, and duration between stops.
    Thread UID can be obtained from search_routes() results.
    """
    params = {"uid": uid, "lang": lang}
    if date:
        params["date"] = date

    return await _fetch("thread/", params)


@mcp.tool()
async def find_nearest_stations(
    lat: float,
    lng: float,
    distance: float,
    transport_types: str | None = None,
    station_types: str | None = None,
    offset: int = 0,
    limit: int = 50,
    lang: str = "ru_RU",
) -> dict:
    """Find stations near geographic coordinates.

    Returns stations within the specified radius (km) with
    distance, type, transport type, and coordinates.
    """
    params: dict = {
        "lat": lat,
        "lng": lng,
        "distance": distance,
        "offset": offset,
        "limit": limit,
        "lang": lang,
    }
    if transport_types:
        params["transport_types"] = transport_types
    if station_types:
        params["station_types"] = station_types

    return await _fetch("nearest_stations/", params)


@mcp.tool()
async def find_nearest_city(
    lat: float,
    lng: float,
    distance: float = 10,
    lang: str = "ru_RU",
) -> dict:
    """Find the nearest city/town to geographic coordinates.

    Returns city name, code (for use in search_routes), and coordinates.
    """
    params: dict = {
        "lat": lat,
        "lng": lng,
        "distance": distance,
        "lang": lang,
    }
    return await _fetch("nearest_settlement/", params)


@mcp.tool()
async def get_carrier_info(
    code: str,
    system: str = "yandex",
    lang: str = "ru_RU",
) -> dict:
    """Get information about a transport carrier.

    Returns carrier name, contacts, website, IATA/ICAO codes.
    """
    params: dict = {
        "code": code,
        "system": system,
        "lang": lang,
    }
    return await _fetch("carrier/", params)


@mcp.tool()
async def search_stations(query: str, limit: int = 20) -> list:
    """Search stations by name (cached on first call).

    Use this to find station codes for search_routes().
    Returns matching stations with code, title, type, and location.
    Downloads ~40MB reference data on the very first call.
    """
    await _ensure_cache()

    conn = sqlite3.connect(str(CACHE_DB))
    cur = conn.execute(
        "SELECT code, title, station_type, transport_type, lat, lng, settlement "
        "FROM stations WHERE title LIKE ? OR settlement LIKE ? "
        "ORDER BY title LIMIT ?",
        (f"%{query}%", f"%{query}%", limit),
    )
    rows = cur.fetchall()
    conn.close()

    columns = ["code", "title", "station_type", "transport_type", "lat", "lng", "settlement"]
    return [dict(zip(columns, row)) for row in rows]


@mcp.tool()
async def update_stations_cache() -> str:
    """Force re-download and rebuild the stations search cache."""
    if CACHE_DB.exists():
        CACHE_DB.unlink()
    await _build_cache()
    return f"Cached {_cache_count()} stations"


def _cache_count() -> int:
    if not _cache_exists():
        return 0
    conn = sqlite3.connect(str(CACHE_DB))
    (count,) = conn.execute("SELECT COUNT(*) FROM stations").fetchone()
    conn.close()
    return count


@mcp.tool()
async def get_copyright() -> dict:
    """Get copyright attribution data for Yandex Rasp.

    Must be displayed when using Yandex Rasp data in your app.
    """
    return await _fetch("copyright/")


# ── Prompts ─────────────────────────────────────────────────────────

@mcp.prompt()
def plan_trip(from_city: str, to_city: str, date: str | None = None) -> str:
    """Plan a trip between two cities using Yandex Rasp."""
    date_hint = f" on {date}" if date else ""
    return (
        f"Plan a trip from {from_city} to {to_city}{date_hint}. "
        "First search for stations matching these cities using search_stations(), "
        "then use search_routes() with the found station codes to get available routes. "
        "For each route, summarize: departure time, arrival time, duration, "
        "transport type, carrier, and ticket prices if available. "
        "Present the results in a clear, organized way."
    )


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    argv = sys.argv[1:]

    if "--http" in argv:
        kwargs: dict = {"transport": "streamable-http", "json_response": True}
        for i, arg in enumerate(argv):
            if arg == "--port" and i + 1 < len(argv):
                kwargs["port"] = int(argv[i + 1])
        log.info("Starting HTTP server on port %s", kwargs.get("port", 8000))
        mcp.run(**kwargs)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
