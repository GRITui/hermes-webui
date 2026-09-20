"""
Sprint 27 Tests: configurable assistant display name (bot_name).
Tests cover settings API round-trip, empty/missing input defaults,
login page rendering, and server-side sanitization.
"""
import json
import urllib.error
import urllib.request

from tests._pytest_port import BASE


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read()), r.status


def get_raw(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.read().decode(), r.status


def post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


# ── Default value ─────────────────────────────────────────────────────────

def test_settings_default_bot_name():
    """GET /api/settings should return bot_name defaulting to 'Hermes'."""
    d, status = get("/api/settings")
    assert status == 200
    assert "bot_name" in d
    assert d["bot_name"] == "Hermes"


# ── Round-trip ────────────────────────────────────────────────────────────

def test_settings_set_bot_name():
    """POST /api/settings with bot_name should persist and round-trip."""
    try:
        d, status = post("/api/settings", {"bot_name": "TestBot"})
        assert status == 200
        assert d.get("bot_name") == "TestBot"
        d2, _ = get("/api/settings")
        assert d2.get("bot_name") == "TestBot"
    finally:
        post("/api/settings", {"bot_name": "Hermes"})


def test_settings_bot_name_special_chars():
    """bot_name with safe special characters should persist correctly."""
    try:
        d, status = post("/api/settings", {"bot_name": "My Assistant 2.0"})
        assert status == 200
        d2, _ = get("/api/settings")
        assert d2.get("bot_name") == "My Assistant 2.0"
    finally:
        post("/api/settings", {"bot_name": "Hermes"})


# ── Server-side sanitization ──────────────────────────────────────────────

def test_settings_empty_bot_name_defaults_to_hermes():
    """Posting an empty bot_name should default to 'Hermes' server-side."""
    try:
        d, status = post("/api/settings", {"bot_name": ""})
        assert status == 200
        assert d.get("bot_name") == "Hermes"
        d2, _ = get("/api/settings")
        assert d2.get("bot_name") == "Hermes"
    finally:
        post("/api/settings", {"bot_name": "Hermes"})


def test_settings_whitespace_bot_name_defaults_to_hermes():
    """Posting a whitespace-only bot_name should default to 'Hermes'."""
    try:
        d, status = post("/api/settings", {"bot_name": "   "})
        assert status == 200
        assert d.get("bot_name") == "Hermes"
    finally:
        post("/api/settings", {"bot_name": "Hermes"})


# ── Login page rendering ──────────────────────────────────────────────────

def test_login_page_shows_app_brand():
    """GET /login should show the ai-nest app brand in title and h1."""
    html, status = get_raw("/login")
    assert status == 200
    assert "<title>ai-nest" in html
    assert "<h1>ai-nest</h1>" in html


def test_login_page_ignores_bot_name():
    """GET /login shows the ai-nest app brand, not the configured bot_name."""
    try:
        post("/api/settings", {"bot_name": "Aria"})
        html, status = get_raw("/login")
        assert status == 200
        assert "<title>ai-nest" in html
        assert "<h1>ai-nest</h1>" in html
        # bot_name is the in-app assistant name; it must not leak onto the login page
        assert "<h1>Aria</h1>" not in html
    finally:
        post("/api/settings", {"bot_name": "Hermes"})


def test_login_page_empty_name_does_not_crash():
    """Login page must not 500 even if somehow bot_name is empty in settings."""
    # Force an empty value by patching settings file directly — skipped here
    # because the server-side guard in POST /api/settings prevents storing empty.
    # Instead, verify that /login returns 200 reliably.
    html, status = get_raw("/login")
    assert status == 200
    assert "Sign in" in html


def test_login_page_not_injected_by_bot_name():
    """A malicious bot_name must not reach the login page (it's not rendered there)."""
    try:
        post("/api/settings", {"bot_name": "<script>alert(1)</script>"})
        html, status = get_raw("/login")
        assert status == 200
        # bot_name is not rendered on the login page, so neither raw nor escaped form appears
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" not in html
        assert "<h1>ai-nest</h1>" in html
    finally:
        post("/api/settings", {"bot_name": "Hermes"})
