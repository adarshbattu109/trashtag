import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "t.db"))
    from trashtag.app.serve import app

    return TestClient(app)


def _a_new_issue_id(client):
    for i in client.get("/v1/issues").json()["issues"]:
        if i["status"] == "new":
            return i["id"]
    raise AssertionError("no seeded 'new' issue")


def test_patch_verifies(client):
    iid = _a_new_issue_id(client)
    r = client.patch(f"/v1/issues/{iid}", json={"status": "verified"})
    assert r.status_code == 200 and r.json()["status"] == "verified"


def test_patch_illegal_transition_422(client):
    iid = _a_new_issue_id(client)
    client.patch(f"/v1/issues/{iid}", json={"status": "verified"})
    assert client.patch(f"/v1/issues/{iid}", json={"status": "new"}).status_code == 422


def test_patch_invalid_value_422(client):
    iid = _a_new_issue_id(client)
    assert (
        client.patch(f"/v1/issues/{iid}", json={"severity": "apocalyptic"}).status_code
        == 422
    )


def test_patch_missing_404(client):
    assert (
        client.patch("/v1/issues/iss_nope", json={"status": "verified"}).status_code
        == 404
    )
