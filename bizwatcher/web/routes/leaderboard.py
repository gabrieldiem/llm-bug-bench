"""Routes for the sortable model leaderboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.leaderboard import compute_leaderboard, sort_leaderboard
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/leaderboard", response_class=HTMLResponse)
def handle_leaderboard(
    request: Request,
    results_dir: str = Depends(get_results_dir),
    sort: str = "score",
    order: str = "desc",
):
    """Render the full leaderboard page with sortable columns."""
    entries = compute_leaderboard(results_dir)
    entries = sort_leaderboard(entries, sort_by=sort, descending=(order == "desc"))

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "leaderboard.html",
        {
            "request": request,
            "entries": entries,
            "sort": sort,
            "order": order,
        },
    )


@router.get("/api/leaderboard", response_class=HTMLResponse)
def api_leaderboard_partial(
    request: Request,
    results_dir: str = Depends(get_results_dir),
    sort: str = "score",
    order: str = "desc",
):
    """Return the leaderboard table as an HTMX partial for in-place sorting."""
    entries = compute_leaderboard(results_dir)
    entries = sort_leaderboard(entries, sort_by=sort, descending=(order == "desc"))

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "partials/_leaderboard_table.html",
        {
            "request": request,
            "entries": entries,
            "sort": sort,
            "order": order,
        },
    )
