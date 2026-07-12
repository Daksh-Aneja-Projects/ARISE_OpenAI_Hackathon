"""
ARISE Live Telemetry Collector — global in-process metrics singleton.

This module provides a lightweight, zero-dependency metrics collector
that the rest of the app increments on key events. The telemetry
WebSocket streams these metrics to the frontend every second.

Usage (from any module):
    from app.telemetry import telemetry
    telemetry.record_agent_call("intake", bid_id="abc123", duration_ms=1240)
    telemetry.record_llm_call(tokens_in=500, tokens_out=800, provider="openai", model="gpt-4o")
    telemetry.record_error("intake", "LLM rate limit exceeded")
    telemetry.record_event("pipeline_started", {"bid_id": "abc123", "by": "alice"})
"""

import time
import collections
import threading
from dataclasses import dataclass

MAX_EVENTS = 200  # ring buffer size for event log
WINDOW_SECONDS = 60  # time window for rate calculations


@dataclass
class AgentStat:
    name: str
    calls: int = 0
    successes: int = 0
    errors: int = 0
    total_duration_ms: float = 0.0
    last_called_at: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.calls if self.calls else 0.0

    @property
    def error_rate(self) -> float:
        return self.errors / self.calls if self.calls else 0.0


class TelemetryCollector:
    """
    Thread-safe in-process metrics collector.
    All data is in-memory — restarts clear history.
    For persistent metrics, swap this for Prometheus/StatsD in production.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._started_at = time.time()

        # Counters
        self.total_agent_calls: int = 0
        self.total_llm_calls: int = 0
        self.total_tokens_in: int = 0
        self.total_tokens_out: int = 0
        self.total_pipeline_runs: int = 0
        self.total_errors: int = 0
        self.total_requests: int = 0

        # Per-agent stats
        self.agent_stats: dict[str, AgentStat] = {}

        # Per-provider LLM counts
        self.provider_calls: dict[str, int] = {}

        # Time-series: ring buffers — each entry is (timestamp, value)
        self._ts_agent_calls: collections.deque = collections.deque(
            maxlen=120
        )  # 2min @1s
        self._ts_llm_calls: collections.deque = collections.deque(maxlen=120)
        self._ts_tokens: collections.deque = collections.deque(maxlen=120)
        self._ts_errors: collections.deque = collections.deque(maxlen=120)
        self._ts_requests: collections.deque = collections.deque(maxlen=120)

        # Rate trackers (counts in current second)
        self._cur_second = int(time.time())
        self._cur_agent_calls = 0
        self._cur_llm_calls = 0
        self._cur_tokens = 0
        self._cur_errors = 0
        self._cur_requests = 0

        # Event log
        self._events: collections.deque = collections.deque(maxlen=MAX_EVENTS)

        # Active pipelines set
        self.active_pipelines: dict[str, dict] = {}  # bid_id -> {stage, started_at}

    # ── Tick — called each second by the WS loop ──────────────────────────
    def tick(self) -> dict:
        """
        Advance the time series by one second.
        Returns the snapshot payload to broadcast.
        Returns current-second values and appends to history.
        """
        with self._lock:
            now = int(time.time())
            if now > self._cur_second:
                # Flush current-second buckets into time series
                self._ts_agent_calls.append(self._cur_agent_calls)
                self._ts_llm_calls.append(self._cur_llm_calls)
                self._ts_tokens.append(self._cur_tokens)
                self._ts_errors.append(self._cur_errors)
                self._ts_requests.append(self._cur_requests)
                # Reset
                self._cur_agent_calls = 0
                self._cur_llm_calls = 0
                self._cur_tokens = 0
                self._cur_errors = 0
                self._cur_requests = 0
                self._cur_second = now

            uptime = int(time.time() - self._started_at)
            return {
                "ts": now,
                "uptime_seconds": uptime,
                # All-time totals
                "totals": {
                    "agent_calls": self.total_agent_calls,
                    "llm_calls": self.total_llm_calls,
                    "tokens_in": self.total_tokens_in,
                    "tokens_out": self.total_tokens_out,
                    "pipeline_runs": self.total_pipeline_runs,
                    "errors": self.total_errors,
                    "requests": self.total_requests,
                },
                # Current-second rates (last complete second)
                "rates": {
                    "agent_calls_sec": list(self._ts_agent_calls)[-1]
                    if self._ts_agent_calls
                    else 0,
                    "llm_calls_sec": list(self._ts_llm_calls)[-1]
                    if self._ts_llm_calls
                    else 0,
                    "tokens_sec": list(self._ts_tokens)[-1] if self._ts_tokens else 0,
                    "errors_sec": list(self._ts_errors)[-1] if self._ts_errors else 0,
                    "requests_sec": list(self._ts_requests)[-1]
                    if self._ts_requests
                    else 0,
                },
                # Rolling 60-second time series (most recent last)
                "series": {
                    "agent_calls": list(self._ts_agent_calls)[-60:],
                    "llm_calls": list(self._ts_llm_calls)[-60:],
                    "tokens": list(self._ts_tokens)[-60:],
                    "errors": list(self._ts_errors)[-60:],
                    "requests": list(self._ts_requests)[-60:],
                },
                # Per-agent stats
                "agents": {
                    name: {
                        "calls": s.calls,
                        "errors": s.errors,
                        "avg_ms": round(s.avg_duration_ms),
                        "error_rate": round(s.error_rate * 100, 1),
                    }
                    for name, s in sorted(self.agent_stats.items())
                },
                # Active pipelines
                "active_pipelines": [
                    {
                        "bid_id": bid_id,
                        "stage": info.get("stage"),
                        "elapsed_s": int(
                            time.time() - info.get("started_at", time.time())
                        ),
                    }
                    for bid_id, info in self.active_pipelines.items()
                ],
                # Provider breakdown
                "providers": dict(self.provider_calls),
                # Recent events
                "events": list(self._events)[-30:],
            }

    # ── Event recording methods ───────────────────────────────────────────
    def record_agent_call(
        self,
        agent_name: str,
        bid_id: str = "",
        duration_ms: float = 0.0,
        success: bool = True,
    ):
        with self._lock:
            self.total_agent_calls += 1
            self._cur_agent_calls += 1
            if agent_name not in self.agent_stats:
                self.agent_stats[agent_name] = AgentStat(name=agent_name)
            s = self.agent_stats[agent_name]
            s.calls += 1
            s.last_called_at = time.time()
            s.total_duration_ms += duration_ms
            if success:
                s.successes += 1
            else:
                s.errors += 1
                self.total_errors += 1
                self._cur_errors += 1
            self._events.append(
                {
                    "t": int(time.time()),
                    "type": "agent",
                    "agent": agent_name,
                    "bid_id": bid_id,
                    "duration_ms": round(duration_ms),
                    "ok": success,
                }
            )

    def record_llm_call(
        self,
        tokens_in: int = 0,
        tokens_out: int = 0,
        provider: str = "unknown",
        model: str = "",
    ):
        with self._lock:
            self.total_llm_calls += 1
            self._cur_llm_calls += 1
            self.total_tokens_in += tokens_in
            self.total_tokens_out += tokens_out
            self._cur_tokens += tokens_in + tokens_out
            self.provider_calls[provider] = self.provider_calls.get(provider, 0) + 1
            self._events.append(
                {
                    "t": int(time.time()),
                    "type": "llm",
                    "provider": provider,
                    "model": model,
                    "tokens": tokens_in + tokens_out,
                }
            )

    def record_pipeline_start(self, bid_id: str, stage: str = ""):
        with self._lock:
            self.total_pipeline_runs += 1
            self.active_pipelines[bid_id] = {"stage": stage, "started_at": time.time()}
            self._events.append(
                {"t": int(time.time()), "type": "pipeline_start", "bid_id": bid_id}
            )

    def record_pipeline_stage(self, bid_id: str, stage: str):
        with self._lock:
            if bid_id in self.active_pipelines:
                self.active_pipelines[bid_id]["stage"] = stage
            self._events.append(
                {
                    "t": int(time.time()),
                    "type": "stage",
                    "bid_id": bid_id,
                    "stage": stage,
                }
            )

    def record_pipeline_end(self, bid_id: str, status: str = "completed"):
        with self._lock:
            self.active_pipelines.pop(bid_id, None)
            self._events.append(
                {
                    "t": int(time.time()),
                    "type": "pipeline_end",
                    "bid_id": bid_id,
                    "status": status,
                }
            )

    def record_request(self):
        with self._lock:
            self.total_requests += 1
            self._cur_requests += 1

    def record_error(self, source: str = "", message: str = ""):
        with self._lock:
            self.total_errors += 1
            self._cur_errors += 1
            self._events.append(
                {
                    "t": int(time.time()),
                    "type": "error",
                    "source": source,
                    "msg": message[:120],
                }
            )

    def record_event(self, kind: str, data: dict = {}):
        with self._lock:
            self._events.append({"t": int(time.time()), "type": kind, **data})


# Global singleton — import this everywhere
telemetry = TelemetryCollector()
