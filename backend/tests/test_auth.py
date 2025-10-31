from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_token_endpoint():
    app = create_app()
    client = TestClient(app)
    r = client.post("/v1/auth/token", json={"username": "dev", "password": "dev"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data


