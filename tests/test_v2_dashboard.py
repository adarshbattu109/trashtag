import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "t.db"))
    from trashtag.app.serve import app

    return TestClient(app)


def test_dashboard_fetches_live_endpoints(client):
    html = client.get("/").text
    assert "/v1/issues" in html  # fetches live issues
    assert "/evidence" in html  # references the evidence image endpoint
    assert "PATCH" in html or "method:" in html  # performs updates
    # the hardcoded mock array is no longer the render source of truth:
    assert "const MOCK_ISSUES" not in html
