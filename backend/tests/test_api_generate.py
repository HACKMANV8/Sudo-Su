from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_post_generate_returns_202():
    app = create_app()
    client = TestClient(app)
    body = {
        "schema": {"n_rows": 10, "fields": [{"name": "id", "type": "string"}]},
        "mode": "generate",
        "target_rows": 10,
        "seed": "t",
    }
    r = client.post("/v1/generate", json=body)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data and data["status"] == "PENDING"


