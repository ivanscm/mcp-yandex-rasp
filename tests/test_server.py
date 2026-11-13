import pytest
import respx
import server


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(server, "API_KEY", "test-key")
    server._HTTP_CLIENT = None
    if server._cache_exists():
        server.CACHE_DB.unlink(missing_ok=True)


@pytest.fixture()
def mock_api():
    with respx.mock(base_url=server.BASE_URL) as mock:
        yield mock


# ── search_routes ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_search_routes(mock_api):
    mock_api.get("/search/").respond(
        json={
            "pagination": {"total": 1, "limit": 100, "offset": 0},
            "segments": [
                {
                    "from": {"code": "s9600213", "title": "Шереметьево"},
                    "to": {"code": "s9600396", "title": "Симферополь"},
                    "departure": "2025-06-01T06:00:00+03:00",
                    "arrival": "2025-06-01T10:15:00+03:00",
                    "duration": 8100,
                    "thread": {
                        "number": "SU 1827",
                        "title": "Москва - Симферополь",
                        "transport_type": "plane",
                    },
                }
            ],
            "search": {"from": {"code": "c213"}, "to": {"code": "c146"}},
        }
    )

    result = await server.mcp.call_tool(
        "search_routes", {"from_": "c213", "to": "c146"}
    )
    assert result is not None


# ── get_station_schedule ────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_station_schedule(mock_api):
    mock_api.get("/schedule/").respond(
        json={
            "station": {"code": "s9600213", "title": "Шереметьево"},
            "schedule": [
                {
                    "thread": {"uid": "test_uid", "title": "Москва - СПб"},
                    "departure": "2025-06-01T06:00:00+03:00",
                    "arrival": "2025-06-01T10:00:00+03:00",
                }
            ],
            "pagination": {"total": 1, "limit": 100, "offset": 0},
        }
    )

    result = await server.mcp.call_tool(
        "get_station_schedule", {"station": "s9600213", "transport_types": "plane"}
    )
    assert result is not None


# ── get_thread_stops ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_thread_stops(mock_api):
    mock_api.get("/thread/").respond(
        json={
            "uid": "test_uid",
            "title": "Москва - СПб",
            "stops": [
                {
                    "station": {
                        "code": "s2006004",
                        "title": "Москва (Ленинградский вокзал)",
                    },
                    "departure": "2025-06-01T00:44:00+03:00",
                    "duration": 0.0,
                }
            ],
        }
    )

    result = await server.mcp.call_tool("get_thread_stops", {"uid": "test_uid"})
    assert result is not None


# ── find_nearest_stations ───────────────────────────────────────────

@pytest.mark.anyio
async def test_find_nearest_stations(mock_api):
    mock_api.get("/nearest_stations/").respond(
        json={
            "pagination": {"total": 1, "limit": 100, "offset": 0},
            "stations": [
                {
                    "code": "s9600213",
                    "title": "Шереметьево",
                    "distance": 5.2,
                    "station_type": "airport",
                    "transport_type": "plane",
                    "lat": 55.972,
                    "lng": 37.414,
                }
            ],
        }
    )

    result = await server.mcp.call_tool(
        "find_nearest_stations", {"lat": 55.972, "lng": 37.414, "distance": 10}
    )
    assert result is not None


# ── find_nearest_city ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_find_nearest_city(mock_api):
    mock_api.get("/nearest_settlement/").respond(
        json={
            "code": "c213",
            "title": "Москва",
            "distance": 0.5,
            "lat": 55.7558,
            "lng": 37.6173,
        }
    )

    result = await server.mcp.call_tool(
        "find_nearest_city", {"lat": 55.7558, "lng": 37.6173}
    )
    assert result is not None


# ── get_carrier_info ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_carrier_info(mock_api):
    mock_api.get("/carrier/").respond(
        json={
            "carriers": [
                {
                    "code": 26,
                    "title": "Аэрофлот",
                    "codes": {"iata": "SU", "icao": None},
                }
            ]
        }
    )

    result = await server.mcp.call_tool(
        "get_carrier_info", {"code": "SU", "system": "iata"}
    )
    assert result is not None


# ── get_copyright ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_copyright(mock_api):
    mock_api.get("/copyright/").respond(
        json={
            "copyright": {
                "text": "Данные предоставлены сервисом Яндекс Расписания",
                "url": "http://rasp.yandex.ru/",
            }
        }
    )

    result = await server.mcp.call_tool("get_copyright", {})
    assert result is not None


# ── search_stations (uses cache) ────────────────────────────────────

@pytest.mark.anyio
async def test_search_stations_empty_cache(mock_api):
    mock_api.get("/stations_list/").respond(
        json={
            "countries": [
                {
                    "title": "Россия",
                    "codes": {"yandex_code": "l225"},
                    "regions": [
                        {
                            "title": "Московская область",
                            "codes": {"yandex_code": "r10705"},
                            "settlements": [
                                {
                                    "title": "Москва",
                                    "codes": {"yandex_code": "c213"},
                                    "stations": [
                                        {
                                            "title": "Москва (Ленинградский вокзал)",
                                            "station_type": "train_station",
                                            "transport_type": "train",
                                            "latitude": 55.776,
                                            "longitude": 37.655,
                                            "codes": {"yandex_code": "s2006004"},
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    result = await server.mcp.call_tool("search_stations", {"query": "Москва"})
    assert result is not None


# ── update_stations_cache ───────────────────────────────────────────

@pytest.mark.anyio
async def test_update_stations_cache(mock_api):
    mock_api.get("/stations_list/").respond(json={"countries": []})

    result = await server.mcp.call_tool("update_stations_cache", {})
    assert result is not None
