import time


class Stats:
    def __init__(self):
        self.latencies = []
        self.errors = 0
        self.start_time = None
        self.end_time = None
        # 5xx attribution by X-App/X-Origin markers (see CLAUDE.md):
        #   app   = X-App + X-Origin  -> real Django 500 (code regression)
        #   infra = only X-Origin     -> gunicorn/nginx
        #   edge  = neither marker    -> Cloudflare edge (not our origin)
        self.err_5xx = {"app": 0, "infra": 0, "edge": 0}

    def start(self):
        self.latencies = []
        self.errors = 0
        self.err_5xx = {"app": 0, "infra": 0, "edge": 0}
        self.start_time = time.monotonic()

    def stop(self):
        self.end_time = time.monotonic()

    def record(self, latency_ms):
        self.latencies.append(latency_ms)

    def record_error(self):
        self.errors += 1

    def classify_5xx(self, headers):
        """Bucket a 5xx by attribution markers. headers: mapping (case-insensitive)."""
        has_app = "X-App" in headers
        has_origin = "X-Origin" in headers
        if has_app and has_origin:
            self.err_5xx["app"] += 1
        elif has_origin:
            self.err_5xx["infra"] += 1
        else:
            self.err_5xx["edge"] += 1

    def duration(self):
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    def total_requests(self):
        return len(self.latencies) + self.errors

    def rps(self):
        d = self.duration()
        if d == 0:
            return 0.0
        return self.total_requests() / d

    def percentile(self, p):
        if not self.latencies:
            return 0.0
        sorted_lats = sorted(self.latencies)
        idx = int(len(sorted_lats) * p / 100)
        idx = min(idx, len(sorted_lats) - 1)
        return sorted_lats[idx]

    def error_rate(self):
        total = self.total_requests()
        if total == 0:
            return 0.0
        return self.errors / total * 100


def print_stats(name, stats, concurrency):
    total = stats.total_requests()
    errors = stats.errors
    error_rate = stats.error_rate()
    rps = stats.rps()
    duration = stats.duration()

    lat_min = min(stats.latencies) if stats.latencies else 0
    p50 = stats.percentile(50)
    p95 = stats.percentile(95)
    p99 = stats.percentile(99)
    lat_max = max(stats.latencies) if stats.latencies else 0

    print()
    print(f"── {name} {'─' * max(1, 50 - len(name))}")
    print(f"  Requests:    {total:,}    Errors: {errors} ({error_rate:.1f}%)")
    e5 = getattr(stats, "err_5xx", None)
    if e5 and sum(e5.values()):
        print(
            f"  5xx attrib:  app={e5['app']} (Django bug)  "
            f"infra={e5['infra']} (gunicorn/nginx)  edge={e5['edge']} (Cloudflare)"
        )
    print(f"  RPS:         {rps:.1f}")
    print(
        f"  Latency:     min={lat_min:.0f}ms  p50={p50:.0f}ms"
        f"  p95={p95:.0f}ms  p99={p99:.0f}ms  max={lat_max:.0f}ms"
    )
    print(f"  Duration:    {duration:.1f}s    Concurrency: {concurrency}")
    print()
