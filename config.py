import argparse

TARGETS = {
    "local": {
        "rest": "http://localhost:8000",
        "ws": "ws://localhost:8443",
    },
    "prod": {
        "rest": "https://tasks.titov.dev",
        "ws": "wss://tasks.titov.dev",
    },
}

DEFAULTS = {
    "concurrency": 10,
    "duration": 10,
    "warmup": 2,
}


def resolve_target(name):
    if name in TARGETS:
        return TARGETS[name]
    # Custom URL: assume REST base, derive WS by swapping scheme
    rest = name.rstrip("/")
    if rest.startswith("https://"):
        ws = "wss://" + rest[len("https://"):]
    else:
        ws = "ws://" + rest[len("http://"):]
    return {"rest": rest, "ws": ws}


def add_common_args(parser):
    parser.add_argument(
        "--target",
        default="local",
        help="Target: local, prod, or custom URL (default: local)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULTS["concurrency"],
        help=f"Number of concurrent workers (default: {DEFAULTS['concurrency']})",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=DEFAULTS["duration"],
        help=f"Test duration in seconds (default: {DEFAULTS['duration']})",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=DEFAULTS["warmup"],
        help=f"Warmup duration in seconds (default: {DEFAULTS['warmup']})",
    )
    return parser
