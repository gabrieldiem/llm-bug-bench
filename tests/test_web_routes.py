"""Basic endpoint tests — no LLM inference required."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_empty(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text or "runs" in resp.text.lower()


def test_dashboard_with_run(client, sample_run):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "test-model" in resp.text


# ---------------------------------------------------------------------------
# Test cases (benchmark CRUD via /tests routes)
# ---------------------------------------------------------------------------


def test_test_list_empty(client):
    resp = client.get("/tests")
    assert resp.status_code == 200


def test_test_list_with_cases(client, sample_benchmark):
    resp = client.get("/tests")
    assert resp.status_code == 200
    assert "py_test_001" in resp.text


def test_test_create(client, tmp_dirs):
    resp = client.post(
        "/api/tests",
        data={
            "id": "new_test_01",
            "title": "New test",
            "language": "go",
            "difficulty": "easy",
            "prompt": "Find the bug.",
            "code": "",
            "expected_issues": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/tests/new_test_01" in resp.headers["location"]


def test_test_view(client, sample_benchmark):
    resp = client.get("/tests/py_test_001")
    assert resp.status_code == 200
    assert "Sample test case" in resp.text


def test_test_edit_form(client, sample_benchmark):
    resp = client.get("/tests/py_test_001/edit")
    assert resp.status_code == 200
    assert "py_test_001" in resp.text


def test_test_update(client, sample_benchmark):
    resp = client.post(
        "/api/tests/py_test_001",
        data={
            "id": "py_test_001",
            "title": "Updated title",
            "language": "python",
            "difficulty": "medium",
            "prompt": "Updated prompt.",
            "code": "",
            "expected_issues": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_test_delete(client, sample_benchmark):
    resp = client.delete("/api/tests/py_test_001")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_test_view_missing_redirects(client):
    resp = client.get("/tests/nonexistent", follow_redirects=False)
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# New run form
# ---------------------------------------------------------------------------


def test_new_run_form(client):
    resp = client.get("/runs/new")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def test_leaderboard_empty(client):
    resp = client.get("/leaderboard")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Run detail
# ---------------------------------------------------------------------------


def test_run_detail(client, sample_run):
    model_slug, run_id = sample_run
    resp = client.get(f"/run/{model_slug}/{run_id}")
    assert resp.status_code == 200
    assert "test-model" in resp.text


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


def test_compare_form(client):
    resp = client.get("/compare")
    assert resp.status_code == 200
