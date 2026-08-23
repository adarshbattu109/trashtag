"""The app serves the dashboard, the issue API answers and filters, and MCP stays mounted."""


def test_dashboard_serves_html(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert "TrashTag" in response.text


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_issues_returns_all(client):
    body = client.get("/v1/issues").json()

    assert body["count"] == len(body["issues"]) > 0


def test_filter_by_class(client):
    issues = client.get("/v1/issues", params={"class": "pothole"}).json()["issues"]

    assert issues and all(i["class"] == "pothole" for i in issues)


def test_filter_by_status(client):
    issues = client.get("/v1/issues", params={"status": "filed"}).json()["issues"]

    assert issues
    assert all(i["status"] == "filed" for i in issues)


def test_unknown_class_is_422(client):
    assert client.get("/v1/issues", params={"class": "meteorite"}).status_code == 422


def test_unknown_status_is_422(client):
    assert client.get("/v1/issues", params={"status": "in_orbit"}).status_code == 422


def test_combined_filters(client):
    issues = client.get(
        "/v1/issues", params={"class": "pothole", "status": "new"}
    ).json()["issues"]

    assert issues
    assert all(i["class"] == "pothole" and i["status"] == "new" for i in issues)


def test_get_one_issue_round_trips(client):
    first_id = client.get("/v1/issues").json()["issues"][0]["id"]

    response = client.get(f"/v1/issues/{first_id}")

    assert response.status_code == 200
    assert response.json()["id"] == first_id


def test_missing_issue_is_404(client):
    assert client.get("/v1/issues/NOPE").status_code == 404


def test_mcp_is_mounted(app_routes):
    assert "/mcp" in app_routes
