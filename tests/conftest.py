"""Shared fixtures. No test reaches the network — the app serves hardcoded mock data."""

import pytest
from fastapi.testclient import TestClient

from trashtag.app.serve import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def app_routes():
    return {getattr(route, "path", None) for route in app.routes}
