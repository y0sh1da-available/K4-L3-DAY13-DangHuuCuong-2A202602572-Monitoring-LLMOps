from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import tracing_enabled

configure_logging()
log = get_logger()
agent = LabAgent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-monitoring-llmops-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )
    yield


app = FastAPI(title="Day 13 Monitoring & LLMOps Lab", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import json
import statistics


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view() -> str:
    log_path = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
    records = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    latencies = [r["latency_ms"] for r in records if r.get("event") == "response_sent" and "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in records if r.get("event") == "response_sent" and "ttft_ms" in r]
    requests_received = [r for r in records if r.get("event") == "request_received"]
    requests_failed = [r for r in records if r.get("event") == "request_failed"]
    responses_sent = [r for r in records if r.get("event") == "response_sent"]

    def percentile(data: list[int | float], p: float) -> float:
        if not data:
            return 0.0
        s = sorted(data)
        k = (len(s) - 1) * (p / 100.0)
        f = int(k)
        c = f + 1
        if c < len(s):
            return s[f] + (k - f) * (s[c] - s[f])
        return float(s[f])

    p50_lat = round(percentile(latencies, 50), 1)
    p95_lat = round(percentile(latencies, 95), 1)
    p99_lat = round(percentile(latencies, 99), 1)
    p95_ttft = round(percentile(ttfts, 95), 1)

    total_requests = len(requests_received)
    traffic_rate = round(total_requests / 60.0, 2)

    total_errors = len(requests_failed)
    error_rate = round((total_errors / total_requests * 100) if total_requests else 0.0, 2)
    tool_events = [r for r in records if r.get("tool_name") is not None]
    tool_success_count = sum(1 for r in tool_events if r.get("tool_success") is True)
    tool_success_rate = round((tool_success_count / len(tool_events) * 100) if tool_events else 100.0, 1)

    total_cost = round(sum(r.get("cost_usd", 0.0) for r in responses_sent), 4)
    tokens_in = sum(r.get("tokens_in", 0) for r in responses_sent)
    tokens_out = sum(r.get("tokens_out", 0) for r in responses_sent)
    total_tokens = tokens_in + tokens_out

    quality_scores = [r["quality_score"] for r in responses_sent if "quality_score" in r]
    avg_quality = round(statistics.mean(quality_scores), 2) if quality_scores else 0.0

    lat_status = "PASS" if p95_lat <= 3000 else "ALERT"
    traffic_status = "PASS" if total_requests >= 1 else "IDLE"
    err_status = "PASS" if error_rate <= 2.0 else "ALERT"
    cost_status = "PASS" if total_cost <= 2.5 else "ALERT"
    token_status = "PASS" if total_tokens <= 50000 else "ALERT"
    quality_status = "PASS" if avg_quality >= 0.75 else "ALERT"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>K4-L3A Day 13 Monitoring &amp; LLMOps</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .title {{ font-size: 24px; font-weight: 700; color: #38bdf8; }}
        .meta {{ font-size: 14px; color: #94a3b8; }}
        .badge {{ background: #1e293b; border: 1px solid #475569; padding: 4px 10px; border-radius: 6px; font-size: 13px; }}
        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        @media(max-width: 1024px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media(max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .card-title {{ font-size: 15px; font-weight: 600; color: #cbd5e1; }}
        .tag-pass {{ background: #065f46; color: #34d399; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .tag-alert {{ background: #881337; color: #fb7185; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .tag-idle {{ background: #334155; color: #94a3b8; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .val-main {{ font-size: 32px; font-weight: 700; color: #f1f5f9; margin: 8px 0; }}
        .val-sub {{ font-size: 13px; color: #94a3b8; line-height: 1.6; }}
        .threshold {{ margin-top: 12px; padding-top: 10px; border-top: 1px dashed #334155; font-size: 12px; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">K4-L3A Day 13 Monitoring &amp; LLMOps</div>
            <div class="meta">Service: day13-l3a-monitoring-llmops-lab | Model: {agent.model}</div>
        </div>
        <div style="display: flex; gap: 10px;">
            <span class="badge">Time Range: <b>Last 60 Minutes</b></span>
            <span class="badge">Refresh: <b>30s</b></span>
            <span class="badge">Records: <b>{len(records)}</b></span>
        </div>
    </div>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency percentiles &amp; TTFT</span>
                <span class="tag-{lat_status.lower()}">{lat_status}</span>
            </div>
            <div class="val-main">{p95_lat} <span style="font-size: 16px; color: #94a3b8;">ms (P95)</span></div>
            <div class="val-sub">
                <div>P50: <b>{p50_lat} ms</b> &nbsp;|&nbsp; P99: <b>{p99_lat} ms</b></div>
                <div>TTFT (Time To First Token) P95: <b>{p95_ttft} ms</b></div>
            </div>
            <div class="threshold">SLO Threshold: P95 &le; 3000 ms</div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request traffic</span>
                <span class="tag-{traffic_status.lower()}">{traffic_status}</span>
            </div>
            <div class="val-main">{total_requests} <span style="font-size: 16px; color: #94a3b8;">requests</span></div>
            <div class="val-sub">
                <div>Average Rate: <b>{traffic_rate} req/min</b></div>
                <div>Active window: <b>60 minutes</b></div>
            </div>
            <div class="threshold">Threshold: Rate &ge; 1 req/min</div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error rate &amp; Retrieval success</span>
                <span class="tag-{err_status.lower()}">{err_status}</span>
            </div>
            <div class="val-main">{error_rate}% <span style="font-size: 16px; color: #94a3b8;">error rate</span></div>
            <div class="val-sub">
                <div>Failed requests: <b>{total_errors} / {total_requests}</b></div>
                <div>Retrieval success rate: <b>{tool_success_rate}%</b></div>
            </div>
            <div class="threshold">SLO Threshold: Error rate &le; 2.0% &amp; Retrieval &ge; 90%</div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost over time</span>
                <span class="tag-{cost_status.lower()}">{cost_status}</span>
            </div>
            <div class="val-main">${total_cost:.4f} <span style="font-size: 16px; color: #94a3b8;">USD</span></div>
            <div class="val-sub">
                <div>Cumulative cost: <b>${total_cost:.4f}</b></div>
                <div>Cost rate: <b>${(total_cost/60.0):.6f} / min</b></div>
            </div>
            <div class="threshold">Guardrail Threshold: Total &le; $2.50 USD</div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Input and output tokens</span>
                <span class="tag-{token_status.lower()}">{token_status}</span>
            </div>
            <div class="val-main">{total_tokens:,} <span style="font-size: 16px; color: #94a3b8;">tokens</span></div>
            <div class="val-sub">
                <div>Input Tokens: <b>{tokens_in:,}</b></div>
                <div>Output Tokens: <b>{tokens_out:,}</b></div>
            </div>
            <div class="threshold">Guardrail Threshold: Total &le; 50,000 tokens</div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality proxy</span>
                <span class="tag-{quality_status.lower()}">{quality_status}</span>
            </div>
            <div class="val-main">{avg_quality} <span style="font-size: 16px; color: #94a3b8;">/ 1.00</span></div>
            <div class="val-sub">
                <div>Average Quality Score: <b>{avg_quality}</b></div>
                <div>Evaluated responses: <b>{len(quality_scores)}</b></div>
            </div>
            <div class="threshold">Guardrail Threshold: Mean &ge; 0.75</div>
        </div>
    </div>
</body>
</html>"""


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    # Enrich logs with request context (user_id_hash, session_id, feature, model, env)
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
        env=os.getenv("APP_ENV", "dev"),
    )
    
    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
            correlation_id=request.state.correlation_id,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            ttft_ms=result.ttft_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
            tool_name="retrieval",
            tool_success=True,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            ttft_ms=result.ttft_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            tool_name="retrieval" if isinstance(exc, RuntimeError) else None,
            tool_success=False if isinstance(exc, RuntimeError) else None,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
