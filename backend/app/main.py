import asyncio
import os
import random
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

def _static_dir() -> Path:
    env = os.environ.get("STATIC_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "frontend"


STATIC_DIR = _static_dir()

BANKS = ["bank A", "bank B", "bank C"]

payment_requests_total = Counter(
    "payment_requests_total",
    "Total simulated payment API requests",
    ["endpoint", "outcome", "http_status", "bank"],
)

payment_duration_seconds = Histogram(
    "payment_duration_seconds",
    "End-to-end simulated payment duration including artificial delay",
    ["endpoint", "outcome", "bank"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 6.0, 10.0),
)

payment_in_flight_requests = Gauge(
    "payment_in_flight_requests",
    "Current number of in-flight payment requests",
)


def _record(endpoint: str, outcome: str, http_status: int, duration_s: float, bank: str) -> None:
    payment_requests_total.labels(
        endpoint=endpoint,
        outcome=outcome,
        http_status=str(http_status),
        bank=bank,
    ).inc()
    payment_duration_seconds.labels(endpoint=endpoint, outcome=outcome, bank=bank).observe(duration_s)


app = FastAPI(title="Banking payment simulation API", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/payments/success")
async def payment_success() -> dict:
    bank = random.choice(BANKS)
    payment_in_flight_requests.inc()
    try:
        t0 = time.perf_counter()
        delay = random.uniform(0.05, 0.2)
        await asyncio.sleep(delay)
        duration = time.perf_counter() - t0
        _record("success", "success", 200, duration, bank)
        return {
            "status": "ok",
            "message": f"Payment completed by {bank}",
            "bank": bank,
            "latency_ms": round(duration * 1000, 2),
        }
    finally:
        payment_in_flight_requests.dec()


@app.post("/api/payments/fail")
async def payment_fail() -> dict:
    bank = random.choice(BANKS)
    payment_in_flight_requests.inc()
    try:
        t0 = time.perf_counter()
        await asyncio.sleep(random.uniform(0.03, 0.12))
        duration = time.perf_counter() - t0
        _record("fail", "failed", 402, duration, bank)
        raise HTTPException(
            status_code=402,
            detail={
                "status": "declined",
                "message": f"Simulated payment declined by {bank}",
                "bank": bank,
                "latency_ms": round(duration * 1000, 2),
            },
        )
    finally:
        payment_in_flight_requests.dec()


@app.post("/api/payments/slow")
async def payment_slow() -> dict:
    bank = random.choice(BANKS)
    payment_in_flight_requests.inc()
    try:
        t0 = time.perf_counter()
        await asyncio.sleep(5.2)
        duration = time.perf_counter() - t0
        _record("slow", "slow_success", 200, duration, bank)
        return {
            "status": "ok",
            "message": f"Payment completed after slow processing by {bank}",
            "bank": bank,
            "latency_ms": round(duration * 1000, 2),
        }
    finally:
        payment_in_flight_requests.dec()


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
