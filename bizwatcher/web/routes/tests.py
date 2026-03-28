from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ...core.loader import (
    delete_test,
    get_all_tags,
    load_test_by_id,
    load_tests,
    save_test,
    update_test,
)
from ...exceptions import DuplicateTestIdError, TestNotFoundError
from ...models import TestCase
from ..dependencies import get_tests_dir

router = APIRouter()


@router.get("/tests", response_class=HTMLResponse)
def handle_test_list(
    request: Request,
    tests_dir: str = Depends(get_tests_dir),
    language: str | None = None,
    tag: str | None = None,
    difficulty: str | None = None,
):
    tags_filter = [tag] if tag else None
    all_cases = load_tests(tests_dir, tags=tags_filter)

    if language:
        all_cases = [t for t in all_cases if t.language == language]
    if difficulty:
        all_cases = [t for t in all_cases if t.difficulty == difficulty]

    all_tags = get_all_tags(tests_dir)
    languages = sorted({t.language for t in load_tests(tests_dir)})
    difficulties = sorted({t.difficulty for t in load_tests(tests_dir)})

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tests/list.html",
        {
            "request": request,
            "tests": all_cases,
            "all_tags": all_tags,
            "languages": languages,
            "difficulties": difficulties,
            "filter_language": language,
            "filter_tag": tag,
            "filter_difficulty": difficulty,
        },
    )


@router.get("/tests/new", response_class=HTMLResponse)
def handle_test_form(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tests/form.html",
        {"request": request, "test": None, "edit_mode": False, "error": None},
    )


@router.get("/tests/{test_id}/edit", response_class=HTMLResponse)
def handle_test_edit(
    test_id: str,
    request: Request,
    tests_dir: str = Depends(get_tests_dir),
):
    try:
        test = load_test_by_id(tests_dir, test_id)
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
    tests_dir: str = Depends(get_tests_dir),
):
    try:
        test = load_test_by_id(tests_dir, test_id)
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
    tests_dir: str = Depends(get_tests_dir),
    id: str = Form(...),
    title: str = Form(...),
    language: str = Form(...),
    tags: str = Form(""),
    difficulty: str = Form("medium"),
    prompt: str = Form(...),
    code: str = Form(""),
    expected_issues: str = Form(""),
    notes: str = Form(""),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    issues_list = [i.strip() for i in expected_issues.split("\n") if i.strip()]

    test = TestCase(
        id=id.strip(),
        title=title.strip(),
        language=language.strip(),
        tags=tag_list,
        difficulty=difficulty.strip(),
        prompt=prompt,
        code=code if code.strip() else None,
        expected_issues=issues_list,
        notes=notes if notes.strip() else None,
    )

    try:
        save_test(tests_dir, test)
    except DuplicateTestIdError as e:
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
    tests_dir: str = Depends(get_tests_dir),
    id: str = Form(...),
    title: str = Form(...),
    language: str = Form(...),
    tags: str = Form(""),
    difficulty: str = Form("medium"),
    prompt: str = Form(...),
    code: str = Form(""),
    expected_issues: str = Form(""),
    notes: str = Form(""),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    issues_list = [i.strip() for i in expected_issues.split("\n") if i.strip()]

    test = TestCase(
        id=id.strip(),
        title=title.strip(),
        language=language.strip(),
        tags=tag_list,
        difficulty=difficulty.strip(),
        prompt=prompt,
        code=code if code.strip() else None,
        expected_issues=issues_list,
        notes=notes if notes.strip() else None,
    )

    try:
        update_test(tests_dir, test_id, test)
    except TestNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)

    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.delete("/api/tests/{test_id}")
def api_delete_test(
    test_id: str,
    tests_dir: str = Depends(get_tests_dir),
):
    try:
        delete_test(tests_dir, test_id)
        return JSONResponse({"ok": True})
    except TestNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
