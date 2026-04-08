# MCP Weather Server

A Model Context Protocol (MCP) server that exposes US weather data via the [National Weather Service API](https://api.weather.gov).

## Tools

- `get_alerts(state)` — Get active weather alerts for a US state (e.g. `CA`, `NY`)
- `get_forecast(latitude, longitude)` — Get a 5-period weather forecast for a location

## Setup

```bash
uv sync
```

## Running

**Weather MCP server:**
```bash
uv run weather.py
```

**Simple greeting server:**
```bash
uv run my_server.py
```

**Test client:**
```bash
uv run my_client.py
```

## Requirements

- Python >= 3.11
- Dependencies: `fastmcp`, `httpx`, `mcp[cli]`
