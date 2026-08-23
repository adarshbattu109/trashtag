import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "t.db"))
    from trashtag.app.serve import app
    return TestClient(app)


def test_issues_served_from_db_seed(client):
    body = client.get("/v1/issues").json()
    assert body["count"] > 0                      # seeded from mock on first read
    assert all("lat" in i and "class" in i for i in body["issues"])


def test_filter_by_class_from_db(client):
    issues = client.get("/v1/issues", params={"class": "pothole"}).json()["issues"]
    assert issues and all(i["class"] == "pothole" for i in issues)


def test_get_one_issue_from_db(client):
    first = client.get("/v1/issues").json()["issues"][0]["id"]
    assert client.get(f"/v1/issues/{first}").json()["id"] == first


def test_unknown_issue_404(client):
    assert client.get("/v1/issues/iss_nope").status_code == 404
