"""Routes for llama.cpp server management — status, model info, and URL configuration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ...core.llamacpp_manager import LlamaCppManager
from ...exceptions import LlamaCppConnectionError
from ..dependencies import get_llamacpp_url

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_manager(llamacpp_url: str = Depends(get_llamacpp_url)) -> LlamaCppManager:
    """Build a LlamaCppManager from the current llama.cpp URL."""
    return LlamaCppManager(base_url=llamacpp_url)


@router.get("/llamacpp", response_class=HTMLResponse)
async def handle_server_page(
    request: Request,
    manager: LlamaCppManager = Depends(_get_manager),
):
    """Render the llama.cpp server management page."""
    templates = request.app.state.templates
    llamacpp_url = request.app.state.llamacpp_url
    try:
        info = await manager.get_server_info()
        error = None
    except LlamaCppConnectionError as e:
        info = None
        error = str(e)
        logger.warning("llama.cpp connection failed: %s", e)

    return templates.TemplateResponse(
        "llamacpp/server.html",
        {
            "request": request,
            "info": info,
            "error": error,
            "llamacpp_url": llamacpp_url,
        },
    )


@router.get("/api/llamacpp/models/json")
async def api_list_models_json(
    manager: LlamaCppManager = Depends(_get_manager),
):
    """Return a JSON array of available model names from the llama.cpp server."""
    try:
        models = await manager.list_models()
        return JSONResponse(models)
    except LlamaCppConnectionError:
        return JSONResponse([])


@router.get("/api/llamacpp/status", response_class=HTMLResponse)
async def api_server_status(
    request: Request,
    manager: LlamaCppManager = Depends(_get_manager),
):
    """Return an HTMX partial with the server status card."""
    templates = request.app.state.templates
    try:
        info = await manager.get_server_info()
        error = None
    except LlamaCppConnectionError as e:
        info = None
        error = str(e)

    return templates.TemplateResponse(
        "llamacpp/_server_status.html",
        {"request": request, "info": info, "error": error},
    )


@router.post("/api/llamacpp/url")
async def api_set_llamacpp_url(request: Request):
    """Override the llama.cpp server URL for this server session."""
    body = await request.json()
    url = body.get("url", "").strip().rstrip("/")
    if not url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    request.app.state.llamacpp_url = url
    logger.info("llama.cpp URL changed: %s", url)
    return JSONResponse({"ok": True, "url": url})
