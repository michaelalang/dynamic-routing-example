import json
import os

import aiohttp
from aiohttp import ClientTimeout, client, web

from frontend import *

BACKEND = os.environ.get("BACKEND", "http://localhost:8080")

baselevel = logging.DEBUG if os.environ.get("DEBUG", False) else logging.INFO
logger = FilteredLogger(__name__, baselevel=baselevel)

instrument()
tracer = trace.get_tracer("frontend")


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
async def backend_system_one(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    logger.info(f"calling backend system prod", _ctx=_ctx)
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = (
            f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        )
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        try:
            async with client.request(
                "GET",
                BACKEND,
                headers={"x-target-env": "prod", "traceparent": traceparent},
                ssl=False,
                timeout=ClientTimeout(5),
            ) as res:
                data = await res.text()
                return web.json_response(
                    json.loads(data), headers={"traceparent": traceparent}
                )
        except Exception as berr:
            return web.Response(
                body=str(berr), status=503, headers={"traceparent": traceparent}
            )


@measure
async def backend_system_two(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    logger.info(f"calling backend system dev", _ctx=_ctx)
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = (
            f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        )
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        try:
            async with client.request(
                "GET",
                BACKEND,
                headers={"x-target-env": "dev", "traceparent": traceparent},
                ssl=False,
                timeout=ClientTimeout(5),
            ) as res:
                data = await res.text()
                return web.json_response(
                    json.loads(data), headers={"traceparent": traceparent}
                )
        except Exception as berr:
            return web.Response(
                body=str(berr), status=503, headers={"traceparent": traceparent}
            )


@measure
async def backend_system_three(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    logger.info(f"calling backend system qa", _ctx=_ctx)
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = (
            f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        )
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        try:
            async with client.request(
                "GET",
                BACKEND,
                headers={"x-target-env": "qa", "traceparent": traceparent},
                ssl=False,
                timeout=ClientTimeout(5),
            ) as res:
                data = await res.text()
                return web.json_response(
                    json.loads(data), headers={"traceparent": traceparent}
                )
        except Exception as berr:
            return web.Response(
                body=str(berr), status=503, headers={"traceparent": traceparent}
            )


@measure
async def frontend_handler(req):
    headers = req.headers.copy()
    traceparent = ""
    _ctx = get_tracecontext(headers=dict(headers))
    with tracer.start_as_current_span(
        "downstream request",
        attributes=dict(headers),
    ) as span:
        _sctx = span.get_span_context()
        TRACINGCALLS_TOTAL.inc()
        traceparent = (
            f"00-{hex(_sctx.trace_id)[2:]}-{hex(_sctx.span_id)[2:]}-0{hex(_sctx.trace_flags)[2:]}"
        )
        span.set_status(StatusCode.OK)
        headers = TraceContextTextMapPropagator().inject(dict(headers), _ctx)
        if headers == None:
            headers = req.headers.copy()
            _ctx = span.get_span_context()
            headers["traceparent"] = (
                f"00-{hex(_ctx.trace_id)[2:]}-{hex(_ctx.span_id)[2:]}-0{hex(_ctx.trace_flags)[2:]}"
            )
        with open("static/main.html") as tmpl:
            html_content = tmpl.read()
    return web.Response(
        text=html_content % (traceparent, traceparent, traceparent, BACKEND),
        content_type="text/html",
        headers={"traceparent": traceparent},
    )


async def app_factory():
    static_path = os.path.join(os.path.dirname(__file__), "static")
    app.router.add_static("/static", static_path)
    app.router.add_get("/", frontend_handler)
    app.router.add_get("/backend1", backend_system_one)
    app.router.add_get("/backend2", backend_system_two)
    app.router.add_get("/backend3", backend_system_three)
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    web.run_app(app_factory(), port=int(os.environ.get("PORT", 8080)))
