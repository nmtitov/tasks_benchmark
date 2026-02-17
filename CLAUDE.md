# CLAUDE.md

## TODO

- **[URGENT]** Production server uses SQLite — `database is locked` errors under concurrent writes (~20-30% error rate at 5 concurrent writers). New server needed. Benchmark confirmed read endpoints are fine (~38 RPS), writes are the bottleneck.

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
