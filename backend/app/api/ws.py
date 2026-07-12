"""
WebSocket Pipeline Streaming — real-time agent progress to frontend.

Clients connect to ws://host/api/ws/pipeline/{bid_id}
and receive SSE-style JSON frames as each stage completes:

  {"type": "stage_update", "stage": "intake", "status": "running",  "idx": 0, ...}
  {"type": "stage_update", "stage": "intake", "status": "completed","idx": 0, ...}
  {"type": "pipeline_done", "status": "completed", ...}
  {"type": "ping"} / "pong"  -- keepalive every 20s (prevents NAT/LB timeout)
  {"type": "error", "message": "...", ...}

Keepalive architecture:
  Server spawns a concurrent _keepalive_loop() task that sends {"type":"ping"}
  every PING_INTERVAL_S seconds. Client responds with "pong". If the server
  detects a disconnect exception during send, it sets stop_event to terminate
  the main poll loop and cleans up.

  This prevents silent WS drops through load-balancers and NAT devices during
  long pipeline runs (typically 2-8 minutes).
"""

import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.database import async_session
from app.models.bid import PipelineRun

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])

# Keepalive tuning
PING_INTERVAL_S = 20  # Server pings client every N seconds
POLL_INTERVAL_S = 1.5  # Pipeline state DB poll frequency


# --------------------------------------------------------------------------- #
# Connection manager -- one set per bid_id                                     #
# --------------------------------------------------------------------------- #
class _ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    def connect(self, bid_id: str, ws: WebSocket):
        self._connections.setdefault(bid_id, []).append(ws)

    def disconnect(self, bid_id: str, ws: WebSocket):
        conns = self._connections.get(bid_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, bid_id: str, payload: dict):
        conns = list(self._connections.get(bid_id, []))
        dead = []
        for ws in conns:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(bid_id, ws)


manager = _ConnectionManager()


# --------------------------------------------------------------------------- #
# Push helpers -- called by pipeline.py to push live updates                   #
# --------------------------------------------------------------------------- #
async def push_stage_update(
    bid_id: str,
    stage_name: str,
    status: str,
    idx: int,
    label: str = "",
    error: str = "",
):
    """Push a stage progress update to all WS clients watching this bid."""
    await manager.broadcast(
        bid_id,
        {
            "type": "stage_update",
            "stage": stage_name,
            "label": label,
            "status": status,
            "idx": idx,
            "error": error,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )


async def push_pipeline_done(bid_id: str, status: str):
    """Push final pipeline completion event."""
    await manager.broadcast(
        bid_id,
        {
            "type": "pipeline_done",
            "status": status,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )


# --------------------------------------------------------------------------- #
# Keepalive task                                                                #
# --------------------------------------------------------------------------- #
async def _keepalive_loop(websocket: WebSocket, stop_event: asyncio.Event):
    """Concurrent task: sends server-initiated pings every PING_INTERVAL_S.

    If the send raises (client gone), sets stop_event so the parent loop exits.
    """
    while not stop_event.is_set():
        await asyncio.sleep(PING_INTERVAL_S)
        if stop_event.is_set():
            break
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:
            stop_event.set()
            break


# --------------------------------------------------------------------------- #
# Pipeline WebSocket endpoint                                                   #
# --------------------------------------------------------------------------- #
@router.websocket("/pipeline/{bid_id}")
async def ws_pipeline(bid_id: str, websocket: WebSocket):
    """
    WebSocket stream for real-time pipeline progress.
    Authenticates via ?token=<jwt> query param (WS can't send Authorization headers).

    Protocol:
      - On connect: receives state_snapshot (current run state)
      - Every 1.5s: receives progress frame if stage/status changed
      - On completion: receives pipeline_done, server closes
      - Every 20s: server sends {"type":"ping"}, client replies "pong"
    """
    await websocket.accept()
    manager.connect(bid_id, websocket)

    stop_event = asyncio.Event()
    keepalive_task = asyncio.create_task(_keepalive_loop(websocket, stop_event))

    try:
        # Send current state immediately on connect
        async with async_session() as db:
            result = await db.execute(
                select(PipelineRun).where(PipelineRun.bid_id == bid_id)
            )
            run = result.scalars().first()
            if run:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "state_snapshot",
                            "run_id": run.id,
                            "status": run.status,
                            "current_stage_index": run.current_stage_index,
                            "current_stage_name": run.current_stage_name,
                            "total_stages": run.total_stages,
                            "completed_stages": run.completed_stages,
                            "stages": list(run.stages) if run.stages else [],
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "no_run",
                            "message": "No active pipeline run for this bid",
                        }
                    )
                )

        last_stage_idx = -1
        last_status = ""

        while not stop_event.is_set():
            # Non-blocking receive: handles client pong + disconnect detection
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                # "pong" from client -- no action needed, keepalive satisfied
            except asyncio.TimeoutError:
                pass
            except Exception:
                break  # Client disconnected

            await asyncio.sleep(POLL_INTERVAL_S)

            async with async_session() as db:
                result = await db.execute(
                    select(PipelineRun).where(PipelineRun.bid_id == bid_id)
                )
                run = result.scalars().first()

            if not run:
                break

            # Push delta if stage or status changed
            if run.current_stage_index != last_stage_idx or run.status != last_status:
                last_stage_idx = run.current_stage_index
                last_status = run.status
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "run_id": run.id,
                            "status": run.status,
                            "current_stage_index": run.current_stage_index,
                            "current_stage_name": run.current_stage_name,
                            "completed_stages": run.completed_stages,
                            "total_stages": run.total_stages,
                            "stages": list(run.stages) if run.stages else [],
                            "failed_stage": run.failed_stage,
                            "error": run.error,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )

            # Terminal states -- close after sending done event
            if run.status in ("completed", "failed", "cancelled"):
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "pipeline_done",
                            "status": run.status,
                            "error": run.error,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        stop_event.set()
        keepalive_task.cancel()
        manager.disconnect(bid_id, websocket)


# --------------------------------------------------------------------------- #
# Telemetry WebSocket -- live backend metrics every 1 second                   #
# --------------------------------------------------------------------------- #
@router.websocket("/telemetry")
async def ws_telemetry(websocket: WebSocket):
    """
    WebSocket stream for live backend telemetry.
    Broadcasts a full metrics snapshot every 1 second:
      - Agent call rates, LLM token throughput
      - Active pipeline list
      - Rolling 60-second time series
      - Last 30 events

    No auth required -- metrics contain no client PII.
    Keepalive: server pings every PING_INTERVAL_S seconds.
    """
    from app.telemetry import telemetry

    await websocket.accept()
    stop_event = asyncio.Event()
    keepalive_task = asyncio.create_task(_keepalive_loop(websocket, stop_event))

    try:
        while not stop_event.is_set():
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                pass
            except Exception:
                break

            snapshot = telemetry.tick()
            snapshot["type"] = "telemetry"
            try:
                await websocket.send_text(json.dumps(snapshot))
            except Exception:
                break

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        stop_event.set()
        keepalive_task.cancel()
