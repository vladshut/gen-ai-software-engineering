"""High-throughput (``--fast``) mode for the deterministic pipeline.

This is an OPTIONAL fast path, separate from the graded file-based protocol in
``integrator.py``. It reuses the three pure agents unchanged but removes the
two bottlenecks that cap throughput at volume:

- **Tier 1 (default) — no per-transaction I/O.** Instead of writing four small
  JSON files per transaction into ``shared/{input,processing,output,results}/``,
  it streams the input as JSONL, runs ``validate -> assess -> settle`` in memory,
  and appends one JSONL line per final record. Input is read line-by-line, so
  memory is O(chunk), not O(N) — a multi-GB file processes on a laptop. This is
  where essentially all the speedup comes from (~40x over the file-based path).
- **Tier 2 (opt-in, ``workers > 1``) — multiple cores.** Each transaction is
  independent, so the stream can be fanned across a ``ProcessPoolExecutor`` in
  chunks (processes, not threads, to sidestep the GIL). This is off by default:
  once file I/O is gone the per-transaction work is tiny, so process-spawn/IPC
  overhead makes it a net loss on small inputs and only a marginal win on very
  large ones. Raise ``workers`` only for genuinely huge batches.

Determinism is preserved: the agents are pure functions with no shared state and
every transaction is independent, so the per-transaction outcome is identical to
the sequential graded run for any worker count. (Sort the output by
``transaction_id`` if you need a stable line order.)
"""

from __future__ import annotations

import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import islice
from pathlib import Path
from typing import Any, Iterator

from agents.fraud_detector import assess_transaction
from agents.settlement_processor import settle_transaction
from agents.transaction_validator import validate_transaction
from integrator import _json_default


def process_one(txn: dict[str, Any]) -> dict[str, Any]:
    """Run a single transaction through the full deterministic agent chain."""
    return settle_transaction(assess_transaction(validate_transaction(txn)))


def process_chunk(chunk: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Process a chunk in a worker process.

    Returns ``(jsonl_line, status)`` pairs so the parent only writes bytes and
    tallies counts — Decimal serialization happens here, in the worker.
    """
    out: list[tuple[str, str]] = []
    for txn in chunk:
        result = process_one(txn)
        line = json.dumps(result, default=_json_default)
        out.append((line, result.get("status", "unknown")))
    return out


def iter_transactions(path: Path) -> Iterator[dict[str, Any]]:
    """Stream transactions from a ``.jsonl`` (one per line) or ``.json`` (array) file.

    JSONL streams line-by-line (O(1) memory); a ``.json`` array is loaded whole
    (kept for compatibility with ``sample-transactions.json``).
    """
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)
    else:
        for txn in json.loads(path.read_text(encoding="utf-8")):
            yield txn


def _chunked(items: Iterator[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    """Yield lists of up to ``size`` items from an iterator (bounded memory)."""
    iterator = iter(items)
    return iter(lambda: list(islice(iterator, size)), [])


def run_scaled(
    input_path: Path,
    output_path: Path,
    *,
    workers: int | None = None,
    chunk_size: int = 10_000,
) -> dict[str, Any]:
    """Stream input -> pure-function chain -> JSONL output.

    Defaults to a single process (Tier 1); pass ``workers > 1`` to fan across a
    process pool (Tier 2). Returns a stats dict: total, settled/held/rejected
    counts, workers, seconds, and per_sec throughput.
    """
    if workers is None:
        workers = 1
    workers = max(1, workers)
    chunk_size = max(1, chunk_size)

    counts: Counter[str] = Counter()
    total = 0
    start = time.perf_counter()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = _chunked(iter_transactions(input_path), chunk_size)

    with output_path.open("w", encoding="utf-8") as out:
        if workers == 1:
            # Single-process path: same logic, no pool overhead (handy for tiny
            # inputs and for debugging).
            for pairs in map(process_chunk, chunks):
                for line, status in pairs:
                    out.write(line)
                    out.write("\n")
                    total += 1
                    counts[status] += 1
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for pairs in pool.map(process_chunk, chunks):
                    for line, status in pairs:
                        out.write(line)
                        out.write("\n")
                        total += 1
                        counts[status] += 1

    seconds = time.perf_counter() - start
    return {
        "total": total,
        "settled": counts.get("settled", 0),
        "held": counts.get("held", 0),
        "rejected": counts.get("rejected", 0),
        "workers": workers,
        "seconds": round(seconds, 3),
        "per_sec": int(total / seconds) if seconds > 0 else total,
    }
