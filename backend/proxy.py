import json
import os

import aiohttp
from aiohttp import ClientTimeout, client, web

from backend import *
from uuid import uuid4

BACKEND = os.environ.get("BACKEND", "http://localhost:8080")

baselevel = logging.DEBUG if os.environ.get("DEBUG", False) else logging.INFO
logger = FilteredLogger(__name__, baselevel=baselevel)

instrument()
tracer = trace.get_tracer("backend")


@web.middleware
async def opentelemetry(request, handler):
    _ctx = get_tracecontext()

    tracer = trace.get_tracer("aiohttp.server")
    with tracer.start_as_current_span(
        "aiohttp.handler", kind=trace.SpanKind.SERVER
    ) as span:
        TRACINGCALLS_TOTAL.inc()
        return await handler(request)


app = web.Application(middlewares=[opentelemetry])

async def metrics(req):
    return web.Response(
        status=200,
        headers={
            "Content-Type": "application/openmetrics-text",
            "MimeType": "application/openmetrics-text",
        },
        body=generate_metrics(),
    )


async def health(req):
    return web.Response(status=200, body="OK")


@measure
async def data(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    logger.info(f"data from backend", _ctx=_ctx)
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        return web.json_response(
                {"namespace": os.environ.get("NAMESPACE"),
                 "app": "product-api",
                 "content": str(uuid4()),
                 "traceid": str(traceparent).split('-')[1]}, headers={"traceparent": traceparent}
        )


@measure
async def backend_handler(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        if headers == None:
            headers = req.headers.copy()
            _ctx = span.get_span_context()
            headers["traceparent"] = (
                f"00-{hex(_ctx.trace_id)[2:]}-{hex(_ctx.span_id)[2:]}-0{hex(_ctx.trace_flags)[2:]}"
            )
    return web.Response(
        text=f"Hello from backend {os.environ.get('NAMESPACE')}",
        content_type="text/html",
        headers={"traceparent": traceparent},
    )


async def app_factory():
    app.router.add_get("/", backend_handler)
    app.router.add_route("*", "/{tail:.*}", data)
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    web.run_app(app_factory(), port=int(os.environ.get("PORT", 8080)))
