from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ...core.ollama_manager import OllamaManager
from ...exceptions import OllamaConnectionError
from ..dependencies import get_ollama_url

router = APIRouter()


def _get_manager(ollama_url: str = Depends(get_ollama_url)) -> OllamaManager:
    return OllamaManager(base_url=ollama_url)


@router.get("/ollama", response_class=HTMLResponse)
async def handle_models_page(
    request: Request,
    manager: OllamaManager = Depends(_get_manager),
):
    templates = request.app.state.templates
    ollama_url = request.app.state.ollama_url
    try:
        models = await manager.list_models()
        error = None
    except OllamaConnectionError as e:
        models = []
        error = str(e)

    return templates.TemplateResponse(
        "ollama/models.html",
        {
            "request": request,
            "models": models,
            "error": error,
            "ollama_url": ollama_url,
        },
    )


@router.get("/api/ollama/models", response_class=HTMLResponse)
async def api_list_models(
    request: Request,
    manager: OllamaManager = Depends(_get_manager),
):
    templates = request.app.state.templates
    try:
        models = await manager.list_models()
        error = None
    except OllamaConnectionError as e:
        models = []
        error = str(e)

    return templates.TemplateResponse(
        "ollama/_model_list.html",
        {"request": request, "models": models, "error": error},
    )


@router.post("/api/ollama/pull")
async def api_pull_model(
    request: Request,
    manager: OllamaManager = Depends(_get_manager),
):
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error": "Model name required"}, status_code=400)

    async def _stream():
        try:
            async for chunk in manager.pull_model(name):
                status = chunk.get("status", "")
                total = chunk.get("total", 0)
                completed = chunk.get("completed", 0)
                pct = round(completed / total * 100) if total else 0
                data = json.dumps(
                    {
                        "status": status,
                        "percent": pct,
                        "completed": completed,
                        "total": total,
                    }
                )
                yield f"data: {data}\n\n"
        except OllamaConnectionError as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
        yield 'data: {"status": "done"}\n\n'

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.delete("/api/ollama/models/{name:path}")
async def api_delete_model(
    name: str,
    manager: OllamaManager = Depends(_get_manager),
):
    try:
        await manager.delete_model(name)
        return JSONResponse({"ok": True})
    except OllamaConnectionError as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@router.post("/api/ollama/url")
async def api_set_ollama_url(request: Request):
    """Allow the UI to override the Ollama URL for this session."""
    body = await request.json()
    url = body.get("url", "").strip().rstrip("/")
    if not url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    request.app.state.ollama_url = url
    return JSONResponse({"ok": True, "url": url})
