#!/usr/bin/env python3
"""End-to-end benchmark simulating realistic Task Studio usage."""

import argparse
import asyncio
import time

import aiohttp

from auth import BenchUser, cleanup_bench_user
from config import add_common_args, resolve_target
from data_gen import gen_group, gen_task_identity, gen_task_schedule, gen_timer
from stats import Stats, print_stats


async def full_workflow(session, base_url, user, stats):
    """Single iteration of the full workflow."""
    headers = user.auth_headers()
    t0 = time.monotonic()

    try:
        # 1. Create a group
        group = gen_group(user.user_id)
        async with session.put(f"{base_url}/api/groups/upsert", json=group, headers=headers) as resp:
            if resp.status not in (200, 201):
                stats.record_error()
                return
            group_data = await resp.json()

        # 2. Create a task identity
        identity = gen_task_identity(user.user_id)
        async with session.put(f"{base_url}/api/task-identities/upsert", json=identity, headers=headers) as resp:
            if resp.status not in (200, 201):
                stats.record_error()
                return
            identity_data = await resp.json()

        # 3. Create a task schedule
        schedule = gen_task_schedule(user.user_id, identity["id"], group["id"])
        async with session.put(f"{base_url}/api/task-schedules/upsert", json=schedule, headers=headers) as resp:
            if resp.status not in (200, 201):
                stats.record_error()
                return
            schedule_data = await resp.json()

        # 4. Start a timer (status=RUN)
        timer = gen_timer(user.user_id, identity["id"], schedule["id"], status="RUN")
        timer_id = timer["id"]
        async with session.put(f"{base_url}/api/timers/upsert", json=timer, headers=headers) as resp:
            if resp.status not in (200, 201):
                stats.record_error()
                return

        # 5. Complete the timer (status=CMP)
        timer["status"] = "CMP"
        timer["updated_at"] = timer["created_at"]  # Will be overwritten by server
        async with session.put(f"{base_url}/api/timers/upsert", json=timer, headers=headers) as resp:
            if resp.status not in (200, 201):
                stats.record_error()
                return

        # 6. Sync download
        async with session.get(f"{base_url}/api/sync/download", headers=headers) as resp:
            if resp.status != 200:
                stats.record_error()
                return
            await resp.read()

        latency_ms = (time.monotonic() - t0) * 1000
        stats.record(latency_ms)

    except Exception:
        stats.record_error()


async def main():
    parser = argparse.ArgumentParser(description="End-to-end benchmark for Task Studio")
    add_common_args(parser)
    parser.add_argument("--cleanup", action="store_true", help="Delete test user after benchmark")
    args = parser.parse_args()

    target = resolve_target(args.target)
    base_url = target["rest"]

    print(f"Target: {base_url}")
    print(f"Concurrency: {args.concurrency}  Duration: {args.duration}s  Warmup: {args.warmup}s")
    print()

    # Create bench user
    print("Setting up...")
    async with aiohttp.ClientSession() as session:
        user = BenchUser(base_url)
        await user.signup(session)
        await user.get_user_id(session)
    print(f"  Created bench user: {user.email} (id: {user.user_id})")

    stop = False

    async def worker(session, collector):
        nonlocal stop
        while not stop:
            await full_workflow(session, base_url, user, collector)

    try:
        async with aiohttp.ClientSession() as session:
            # Warmup
            if args.warmup > 0:
                print("Warming up...")
                warmup_stats = Stats()
                warmup_stats.start()
                stop = False
                workers = [asyncio.create_task(worker(session, warmup_stats)) for _ in range(args.concurrency)]
                await asyncio.sleep(args.warmup)
                stop = True
                await asyncio.gather(*workers, return_exceptions=True)
                warmup_stats.stop()

            # Measurement
            print("Running benchmark...")
            stats = Stats()
            stats.start()
            stop = False
            workers = [asyncio.create_task(worker(session, stats)) for _ in range(args.concurrency)]
            await asyncio.sleep(args.duration)
            stop = True
            await asyncio.gather(*workers, return_exceptions=True)
            stats.stop()

        print_stats("Full workflow (group→identity→schedule→timer→complete→sync)", stats, args.concurrency)

    finally:
        if args.cleanup:
            print("Cleaning up...")
            await cleanup_bench_user(user)


if __name__ == "__main__":
    asyncio.run(main())
