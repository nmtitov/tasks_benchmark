# Task Studio Benchmarks

CLI tools for measuring Task Studio server performance — RPS capacity, latency distribution, and connection limits for both the Django REST API and Dart WebSocket server.

## Setup

```bash
cd tasks_benchmark
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## REST API Benchmarks

```bash
# Run all scenarios against local server
python bench_rest.py --target local --duration 10

# Single scenario
python bench_rest.py --target local --scenario heartbeat --concurrency 10 --duration 10

# Against production
python bench_rest.py --target prod --scenario sync --concurrency 5 --duration 30

# Clean up test user after
python bench_rest.py --target local --duration 5 --cleanup
```

**Scenarios:**

| Scenario | Endpoint | What it measures |
|----------|----------|------------------|
| `heartbeat` | `POST /api/auth/heartbeat` | Baseline latency, framework overhead |
| `sync` | `GET /api/sync/download` | Read performance across 6 tables |
| `upsert_identity` | `PUT /api/task-identities/upsert` | Write performance + notify overhead |
| `upsert_timer` | `PUT /api/timers/upsert` | Write with FK validation + notify |
| `list_timers` | `GET /api/timers` | List/filter performance |
| `all` | All above | Run all scenarios sequentially |

## WebSocket Benchmarks

```bash
# Max concurrent connections
python bench_ws.py --target local --scenario connections --max-connections 100

# Broadcast latency (notify → sync message received)
python bench_ws.py --target local --scenario broadcast --connections 10 --iterations 20

# Connect/disconnect churn rate
python bench_ws.py --target local --scenario churn --duration 10

# All WS scenarios
python bench_ws.py --target local --scenario all --cleanup
```

## Full Workflow Benchmark

Simulates realistic usage: create group, task identity, schedule, start timer, complete timer, sync download.

```bash
python bench_full.py --target local --concurrency 5 --duration 30 --cleanup
```

## Targets

- `--target local` — `http://localhost:8000` / `ws://localhost:8443`
- `--target prod` — `https://tasks.titov.dev` / `wss://tasks.titov.dev`
- `--target http://custom:8000` — custom URL

## Output

```
── REST API: heartbeat ──────────────────────────
  Requests:    1,234    Errors: 0 (0.0%)
  RPS:         123.4
  Latency:     min=2ms  p50=8ms  p95=15ms  p99=22ms  max=45ms
  Duration:    10.0s    Concurrency: 10
```

## Prerequisites

- Django server running: `cd tasks_server && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- WebSocket server running (for WS benchmarks): `cd tasks_websocket && dart run bin/server.dart`
