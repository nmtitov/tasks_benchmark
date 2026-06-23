#!/usr/bin/env python3
"""REST API benchmarks for Task Studio."""

import argparse
import asyncio
import sys
import time

import aiohttp

from auth import BenchUser, cleanup_bench_user
from config import add_common_args, resolve_target
from data_gen import gen_group, gen_task_identity, gen_task_schedule, gen_timer
from stats import Stats, print_stats

# Box-drawing output (─, └, …) crashes on Windows' cp1252 console; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Per-request timeout GUARD. Without it aiohttp's default is 5 min, so under
# saturation a single stalled connection blocks the whole asyncio.gather for
# ~300s (looks like a hang). With a cap, a stall is recorded as an error and the
# worker keeps going — the benchmark stays responsive and the error rate becomes
# a real signal of the server's saturation point.
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)

SCENARIOS = ["heartbeat", "sync", "upsert_identity", "upsert_timer", "list_timers"]


async def run_scenario(name, base_url, user, concurrency, duration, warmup, verbose=False):
    stats = Stats()
    warmup_stats = Stats()
    stop = False
    first_error_logged = False

    # Pre-create entities needed by some scenarios
    pre_identity = None
    pre_schedule = None
    if name in ("upsert_timer", "list_timers"):
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            identity = gen_task_identity(user.user_id)
            url = f"{base_url}/api/task-identities/upsert"
            async with session.put(url, json=identity, headers=user.auth_headers()) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"Pre-create identity failed ({resp.status}): {text}")
                pre_identity = await resp.json()

            schedule = gen_task_schedule(user.user_id, identity["id"])
            url = f"{base_url}/api/task-schedules/upsert"
            async with session.put(url, json=schedule, headers=user.auth_headers()) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"Pre-create schedule failed ({resp.status}): {text}")
                pre_schedule = await resp.json()

    async def log_error(resp):
        nonlocal first_error_logged
        if verbose and not first_error_logged:
            first_error_logged = True
            text = await resp.text()
            xapp = resp.headers.get("X-App", "-")
            xorigin = resp.headers.get("X-Origin", "-")
            print(f"  [ERROR] {resp.status} X-App={xapp} X-Origin={xorigin}: {text[:500]}")

    async def handle(resp, collector):
        # Attribute any 5xx by its X-App/X-Origin markers (see CLAUDE.md) so a
        # Cloudflare-edge 500 is never miscounted as a Django code regression.
        if resp.status >= 500:
            collector.classify_5xx(resp.headers)
            await log_error(resp)

    async def make_request(session, collector):
        if name == "heartbeat":
            url = f"{base_url}/api/auth/heartbeat"
            async with session.post(url, headers=user.auth_headers()) as resp:
                if resp.status not in (200, 204):
                    await handle(resp, collector)
                return resp.status in (200, 204)

        elif name == "sync":
            url = f"{base_url}/api/sync/download"
            async with session.get(url, headers=user.auth_headers()) as resp:
                await resp.read()
                if resp.status != 200:
                    await handle(resp, collector)
                return resp.status == 200

        elif name == "upsert_identity":
            identity = gen_task_identity(user.user_id)
            url = f"{base_url}/api/task-identities/upsert"
            async with session.put(url, json=identity, headers=user.auth_headers()) as resp:
                if resp.status not in (200, 201):
                    await handle(resp, collector)
                return resp.status in (200, 201)

        elif name == "upsert_timer":
            timer = gen_timer(user.user_id, pre_identity["id"], pre_schedule["id"])
            url = f"{base_url}/api/timers/upsert"
            async with session.put(url, json=timer, headers=user.auth_headers()) as resp:
                if resp.status not in (200, 201):
                    await handle(resp, collector)
                return resp.status in (200, 201)

        elif name == "list_timers":
            url = f"{base_url}/api/timers"
            async with session.get(url, headers=user.auth_headers()) as resp:
                await resp.read()
                if resp.status != 200:
                    await handle(resp, collector)
                return resp.status == 200

        return False

    async def worker(session, collector):
        nonlocal stop
        while not stop:
            t0 = time.monotonic()
            try:
                ok = await make_request(session, collector)
                latency_ms = (time.monotonic() - t0) * 1000
                if ok:
                    collector.record(latency_ms)
                else:
                    collector.record_error()
            except Exception:
                collector.record_error()

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        # Warmup phase
        if warmup > 0:
            stop = False
            warmup_stats.start()
            workers = [asyncio.create_task(worker(session, warmup_stats)) for _ in range(concurrency)]
            await asyncio.sleep(warmup)
            stop = True
            await asyncio.gather(*workers, return_exceptions=True)
            warmup_stats.stop()

        # Measurement phase
        stop = False
        stats.start()
        workers = [asyncio.create_task(worker(session, stats)) for _ in range(concurrency)]
        await asyncio.sleep(duration)
        stop = True
        await asyncio.gather(*workers, return_exceptions=True)
        stats.stop()

    print_stats(f"REST API: {name}", stats, concurrency)
    return stats


async def main():
    parser = argparse.ArgumentParser(description="REST API benchmarks for Task Studio")
    add_common_args(parser)
    parser.add_argument(
        "--scenario",
        default="all",
        choices=SCENARIOS + ["all"],
        help="Scenario to run (default: all)",
    )
    parser.add_argument("--cleanup", action="store_true", help="Delete test user after benchmark")
    parser.add_argument("--verbose", action="store_true", help="Print first error response per scenario")
    args = parser.parse_args()

    target = resolve_target(args.target)
    base_url = target["rest"]

    print(f"Target: {base_url}")
    print(f"Concurrency: {args.concurrency}  Duration: {args.duration}s  Warmup: {args.warmup}s")
    print()

    # Create bench user
    print("Setting up...")
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        user = BenchUser(base_url)
        await user.signup(session)
        await user.get_user_id(session)
    print(f"  Created bench user: {user.email} (id: {user.user_id})")

    try:
        scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]
        for scenario in scenarios:
            try:
                await run_scenario(
                    scenario, base_url, user,
                    args.concurrency, args.duration, args.warmup,
                    verbose=args.verbose,
                )
            except Exception as e:
                print(f"\n── REST API: {scenario} {'─' * max(1, 50 - len(scenario))}")
                print(f"  SKIPPED: {e}")
                print()
    finally:
        if args.cleanup:
            print("Cleaning up...")
            await cleanup_bench_user(user)


if __name__ == "__main__":
    asyncio.run(main())
