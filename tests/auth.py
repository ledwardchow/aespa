from __future__ import annotations


def authenticate_client(client, app):
    response = client.post("/api/auth/login", json={"key": app.state.auth.key})
    assert response.status_code == 200
    client.headers["X-AESPA-CSRF"] = response.json()["csrf_token"]
