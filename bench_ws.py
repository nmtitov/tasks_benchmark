#!/usr/bin/env python3
"""WebSocket benchmarks for Task Studio."""

import argparse
import asyncio
import time

import aiohttp
import websockets

from auth import BenchUser, cleanup_bench_user
from config import resolve_target
from stats import Stats, print_stats


async def scenario_connections(ws_url, rest_url, user, max_connections):
    """Ramp up WebSocket connections until failure or max reached."""
    print(f"\n── WS: connections (max={max_connections}) ──────────────────")

    connections = []
    connect_url = f"{ws_url}/ws?token={user.token}"

    for i in range(1, max_connections + 1):
        try:
            ws = await websockets.connect(connect_url)
            connections.append(ws)
            if i % 10 == 0 or i == max_connections:
                print(f"  Connected: {i}/{max_connections}")
        except Exception as e:
            print(f"  Connection failed at {i}: {e}")
            break

    total = len(connections)
    print(f"\n  Max concurrent connections: {total}")

    # Cleanup
    for ws in connections:
        try:
            await ws.close()
        except Exception:
            pass

    print(f"  All connections closed.")
    return total


async def scenario_broadcast(ws_url, rest_url, user, num_connections, iterations):
    """Measure latency from /notify POST to sync message received on N clients."""
    print(f"\n── WS: broadcast (connections={num_connections}, iterations={iterations}) ──")

    connect_url = f"{ws_url}/ws?token={user.token}"
    connections = []

    for i in range(num_connections):
        try:
            ws = await websockets.connect(connect_url)
            connections.append(ws)
        except Exception as e:
            print(f"  Failed to connect client {i + 1}: {e}")
            break

    if not connections:
        print("  No connections established, aborting.")
        return

    print(f"  Connected {len(connections)} clients")
    stats = Stats()
    stats.start()

    notify_url = f"{ws_url}/notify"

    async with aiohttp.ClientSession() as session:
        for i in range(iterations):
            # Trigger a notify
            t0 = time.monotonic()
            try:
                async with session.post(
                    notify_url,
                    json={"user_id": user.user_id},
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status not in (200, 204):
                        stats.record_error()
                        continue
            except Exception:
                stats.record_error()
                continue

            # Wait for all clients to receive the message
            try:
                receive_tasks = [
                    asyncio.wait_for(ws.recv(), timeout=5.0) for ws in connections
                ]
                await asyncio.gather(*receive_tasks)
                latency_ms = (time.monotonic() - t0) * 1000
                stats.record(latency_ms)
            except Exception:
                stats.record_error()

    stats.stop()
    print_stats("WS: broadcast", stats, num_connections)

    for ws in connections:
        try:
            await ws.close()
        except Exception:
            pass

    return stats


async def scenario_churn(ws_url, user, duration):
    """Measure connect/disconnect rate."""
    print(f"\n── WS: churn (duration={duration}s) ──────────────────────")

    connect_url = f"{ws_url}/ws?token={user.token}"
    stats = Stats()
    stats.start()
    end_time = time.monotonic() + duration

    while time.monotonic() < end_time:
        t0 = time.monotonic()
        try:
            ws = await websockets.connect(connect_url)
            await ws.close()
            latency_ms = (time.monotonic() - t0) * 1000
            stats.record(latency_ms)
        except Exception:
            stats.record_error()

    stats.stop()
    print_stats("WS: churn (connect/disconnect)", stats, 1)
    return stats


async def main():
    parser = argparse.ArgumentParser(description="WebSocket benchmarks for Task Studio")
    parser.add_argument("--target", default="local", help="Target: local, prod, or custom URL")
    parser.add_argument(
        "--scenario",
        default="connections",
        choices=["connections", "broadcast", "churn", "all"],
        help="Scenario to run (default: connections)",
    )
    parser.add_argument("--max-connections", type=int, default=100, help="Max connections for connections scenario")
    parser.add_argument("--connections", type=int, default=10, help="Number of connections for broadcast scenario")
    parser.add_argument("--iterations", type=int, default=20, help="Number of broadcast iterations")
    parser.add_argument("--duration", type=int, default=10, help="Duration for churn scenario (seconds)")
    parser.add_argument("--cleanup", action="store_true", help="Delete test user after benchmark")
    args = parser.parse_args()

    target = resolve_target(args.target)
    rest_url = target["rest"]
    ws_url = target["ws"]

    print(f"Target REST: {rest_url}")
    print(f"Target WS:   {ws_url}")
    print()

    # Create bench user
    print("Setting up...")
    async with aiohttp.ClientSession() as session:
        user = BenchUser(rest_url)
        await user.signup(session)
        await user.get_user_id(session)
    print(f"  Created bench user: {user.email} (id: {user.user_id})")

    try:
        scenarios = ["connections", "broadcast", "churn"] if args.scenario == "all" else [args.scenario]

        for scenario in scenarios:
            if scenario == "connections":
                await scenario_connections(ws_url, rest_url, user, args.max_connections)
            elif scenario == "broadcast":
                await scenario_broadcast(ws_url, rest_url, user, args.connections, args.iterations)
            elif scenario == "churn":
                await scenario_churn(ws_url, user, args.duration)
    finally:
        if args.cleanup:
            print("\nCleaning up...")
            await cleanup_bench_user(user)


if __name__ == "__main__":
    asyncio.run(main())
