"""Routes for test case CRUD — list, view, create, update, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ...core.loader import (
    delete_test,
    load_test_by_id,
    load_tests,
    save_test,
    update_test,
)
from ...exceptions import DuplicateTestIdError, TestNotFoundError
from ...models import TestCase
from ..dependencies import get_benchmarks_dir

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tests", response_class=HTMLResponse)
def handle_test_list(
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
    language: str | None = None,
    difficulty: str | None = None,
    sort: str = "id",
    order: str = "asc",
):
    """Render the test case browser with optional filters and sorting."""
    all_cases = load_tests(benchmarks_dir)

    if language:
        all_cases = [t for t in all_cases if t.language == language]
    if difficulty:
        all_cases = [t for t in all_cases if t.difficulty == difficulty]

    all_tests = load_tests(benchmarks_dir)
    languages = sorted({t.language for t in all_tests})
    difficulties = sorted({t.difficulty for t in all_tests})

    key_map: dict = {
        "id": lambda t: t.id.lower(),
        "title": lambda t: t.title.lower(),
        "language": lambda t: t.language.lower(),
        "difficulty": lambda t: {"easy": 0, "medium": 1, "hard": 2}.get(
            t.difficulty, 3
        ),
    }
    key_fn = key_map.get(sort, key_map["id"])
    all_cases = sorted(all_cases, key=key_fn, reverse=(order == "desc"))

    is_htmx = request.headers.get("HX-Request") == "true"
    template = "partials/_tests_table.html" if is_htmx else "tests/list.html"

    templates = request.app.state.templates
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "tests": all_cases,
            "languages": languages,
            "difficulties": difficulties,
            "filter_language": language,
            "filter_difficulty": difficulty,
            "sort": sort,
            "order": order,
        },
    )


@router.get("/tests/new", response_class=HTMLResponse)
def handle_test_form(request: Request):
    """Render the empty test creation form."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tests/form.html",
        {"request": request, "test": None, "edit_mode": False, "error": None},
    )


@router.get("/tests/{test_id}/edit", response_class=HTMLResponse)
def handle_test_edit(
    test_id: str,
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
):
    """Render the test edit form pre-filled with existing data."""
    try:
        test = load_test_by_id(benchmarks_dir, test_id)
    except TestNotFoundError:
        return RedirectResponse("/tests", status_code=302)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tests/form.html",
        {"request": request, "test": test, "edit_mode": True, "error": None},
    )


@router.get("/tests/{test_id}", response_class=HTMLResponse)
def handle_test_view(
    test_id: str,
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
):
    """Render the read-only test case detail page."""
    try:
        test = load_test_by_id(benchmarks_dir, test_id)
    except TestNotFoundError:
        return RedirectResponse("/tests", status_code=302)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tests/detail.html",
        {"request": request, "test": test},
    )


@router.post("/api/tests", response_class=HTMLResponse)
def api_create_test(
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
    id: str = Form(...),
    title: str = Form(...),
    language: str = Form(...),
    difficulty: str = Form("medium"),
    prompt: str = Form(...),
    code: str = Form(""),
    expected_issues: str = Form(""),
    notes: str = Form(""),
):
    """Create a new test case from form data."""
    issues_list = [i.strip() for i in expected_issues.split("\n") if i.strip()]

    test = TestCase(
        id=id.strip(),
        title=title.strip(),
        language=language.strip(),
        difficulty=difficulty.strip(),
        prompt=prompt,
        code=code if code.strip() else None,
        expected_issues=issues_list,
        notes=notes if notes.strip() else None,
    )

    try:
        save_test(benchmarks_dir, test)
        logger.info("Test created via API: %s", test.id)
    except DuplicateTestIdError as e:
        logger.warning("Test creation failed: %s", e)
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "tests/form.html",
            {"request": request, "test": test, "edit_mode": False, "error": str(e)},
            status_code=400,
        )

    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.post("/api/tests/{test_id}", response_class=HTMLResponse)
def api_update_test(
    test_id: str,
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
    id: str = Form(...),
    title: str = Form(...),
    language: str = Form(...),
    difficulty: str = Form("medium"),
    prompt: str = Form(...),
    code: str = Form(""),
    expected_issues: str = Form(""),
    notes: str = Form(""),
):
    """Update an existing test case from form data."""
    issues_list = [i.strip() for i in expected_issues.split("\n") if i.strip()]

    test = TestCase(
        id=id.strip(),
        title=title.strip(),
        language=language.strip(),
        difficulty=difficulty.strip(),
        prompt=prompt,
        code=code if code.strip() else None,
        expected_issues=issues_list,
        notes=notes if notes.strip() else None,
    )

    try:
        update_test(benchmarks_dir, test_id, test)
        logger.info("Test updated via API: %s", test_id)
    except TestNotFoundError as e:
        logger.warning("Test update failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=404)

    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.delete("/api/tests/{test_id}")
def api_delete_test(
    test_id: str,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
):
    """Delete a test case YAML file."""
    try:
        delete_test(benchmarks_dir, test_id)
        logger.info("Test deleted via API: %s", test_id)
        return JSONResponse({"ok": True})
    except TestNotFoundError as e:
        logger.warning("Test delete failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=404)
