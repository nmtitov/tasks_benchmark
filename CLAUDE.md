# CLAUDE.md

## Production Server

RackNerd VPS: 4 cores, 2GB RAM, 9 Gunicorn workers. PostgreSQL (migrated from SQLite). Ping from dev machine ~70ms (Colombia→USA).

### Optimizations applied (2026-03-18)
- `CONN_MAX_AGE=600` — persistent DB connections
- Async WebSocket notification — daemon thread, doesn't block API response
- Unix sockets — both gunicorn and PostgreSQL

### Benchmark results (concurrency 10, server time = p50 - heartbeat)
| Endpoint | p50 | Server time |
|---|---|---|
| heartbeat | 143ms | ~0ms |
| upsert_identity | 178ms | ~35ms |
| upsert_timer | 181ms | ~38ms |
| list_timers | 510ms | ~367ms |

At concurrency 50: CPU saturates at 100%, upsert p50 ~470ms, 220 RPS on reads, 0% errors. 5 vs 9 workers — negligible difference at concurrency 10, 9 workers ~15% faster at concurrency 50.

## Project Overview

Python CLI benchmarking tools for Task Studio servers (Django REST API + Dart WebSocket).

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python bench_rest.py --target local --duration 10
python bench_ws.py --target local --scenario connections
python bench_full.py --target local --duration 10
```

## Commit Attribution

**NEVER add a co-author trailer to commits or PRs.** Do not add `Co-Authored-By: Claude ...` (or any Claude/Anthropic attribution) to commit messages or pull request descriptions.
