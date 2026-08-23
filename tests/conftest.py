"""Shared fixtures. No test reaches the network — the app serves hardcoded mock data."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "test.db"))
    from trashtag.app.serve import app

    return TestClient(app)


@pytest.fixture
def app_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "test.db"))
    from trashtag.app.serve import app

    return {getattr(route, "path", None) for route in app.routes}
