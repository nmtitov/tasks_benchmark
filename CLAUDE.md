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

## Benchmark Methodology

**ALWAYS benchmark prod via the Cloudflare domain (`--target prod` → `https://tasks.titov.dev`). Do NOT hit the raw origin IP or localhost-on-server.** This is the only route that matters for us currently: it's the realistic client path and it's apples-to-apples with the existing RESULTS.md tables (which were also taken via the domain). The origin is firewalled (ufw) so only Cloudflare IP ranges reach 80/443 — direct-IP hits time out by design. Don't ask which route; it's always the CF domain.

### 5xx attribution by header (how to read errors)
nginx stamps `X-Origin: tasks` on everything that leaves the origin; Django middleware stamps `X-App: tasks` on everything Django produces. Classify any 5xx by headers:
- **`X-App` + `X-Origin` present** → real Django app-500 (a code bug — a regression).
- **only `X-Origin`** → infra (gunicorn/nginx), not app code.
- **neither marker** → Cloudflare-edge 500 (not our server; do NOT count as a code regression).

Context: the intermittent bare-500 on `/api/auth/signup` under load was caused by nginx `keepalive_timeout 5` (< Cloudflare's origin connection-reuse window) → CF reused a socket nginx had already closed → race → CF-edge 500 while origin logged 201. Fixed `keepalive_timeout 5 → 75` (2026-06-23); 50-concurrent signup 0.5% → 0.00% edge-500.

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
