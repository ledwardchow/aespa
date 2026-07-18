from fastapi.testclient import TestClient

# ---- helpers ----------------------------------------------------------------


def make_site(client: TestClient, **kwargs):
    defaults = {
        "name": "Juice Shop",
        "base_url": "https://juice.local",
        "requires_auth": False,
    }
    return client.post("/api/sites", json={**defaults, **kwargs})


# ---- health -----------------------------------------------------------------


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---- create -----------------------------------------------------------------


def test_create_site_no_auth(client):
    r = make_site(client)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Juice Shop"
    assert data["base_url"] == "https://juice.local/"
    assert data["requires_auth"] is False
    assert data["login_url"] is None
    assert data["credentials"] == []


def test_scan_guidance_round_trips(client):
    guidance = "Log in via /sso then click Enter."
    r = make_site(client, name="Guided", scan_guidance=guidance)
    assert r.status_code == 201
    site_id = r.json()["id"]
    assert r.json()["scan_guidance"] == guidance

    detail = client.get(f"/api/sites/{site_id}").json()
    assert detail["scan_guidance"] == guidance

    upd = client.put(
        f"/api/sites/{site_id}",
        json={
            "name": "Guided",
            "base_url": "https://juice.local",
            "requires_auth": False,
            "scan_guidance": "Updated steps.",
        },
    )
    assert upd.status_code == 200
    assert upd.json()["scan_guidance"] == "Updated steps."


def test_create_site_with_auth_and_credentials(client):
    r = make_site(
        client,
        name="Juice Auth",
        requires_auth=True,
        login_url="https://juice.local/login",
        credentials=[
            {"username": "admin", "password": "admin123", "label": "admin"},
            {"username": "user", "password": "user123", "label": None},
        ],
    )
    assert r.status_code == 201
    data = r.json()
    assert data["requires_auth"] is True
    assert data["login_url"] == "https://juice.local/login"
    assert len(data["credentials"]) == 2
    assert data["credentials"][0]["username"] == "admin"
    assert data["credentials"][0]["label"] == "admin"


def test_create_site_supports_credential_specific_login_urls(client):
    r = make_site(
        client,
        name="Multi Auth",
        requires_auth=True,
        login_url=None,
        credentials=[
            {
                "username": "admin",
                "password": "admin123",
                "login_url": "https://app.local/admin/login",
            },
            {
                "username": "customer",
                "password": "user123",
                "login_url": "https://app.local/customer/login",
            },
        ],
    )

    assert r.status_code == 201
    data = r.json()
    assert data["login_url"] is None
    login_urls = {c["username"]: c["login_url"] for c in data["credentials"]}
    assert login_urls == {
        "admin": "https://app.local/admin/login",
        "customer": "https://app.local/customer/login",
    }


def test_create_site_rejects_missing_credential_login_without_default(client):
    r = make_site(
        client,
        name="Partial Multi Auth",
        requires_auth=True,
        login_url=None,
        credentials=[
            {"username": "admin", "password": "admin123"},
            {
                "username": "customer",
                "password": "user123",
                "login_url": "https://app.local/customer/login",
            },
        ],
    )

    assert r.status_code == 422


def test_create_site_requires_auth_missing_login_url(client):
    r = make_site(client, requires_auth=True)
    assert r.status_code == 422


def test_create_site_no_auth_with_login_url_rejected(client):
    r = make_site(client, requires_auth=False, login_url="https://juice.local/login")
    assert r.status_code == 422


def test_create_site_no_auth_with_credentials_rejected(client):
    r = make_site(
        client,
        requires_auth=False,
        credentials=[{"username": "x", "password": "y"}],
    )
    assert r.status_code == 422


def test_create_duplicate_name(client):
    make_site(client)
    r = make_site(client)
    assert r.status_code == 409


# ---- list / get -------------------------------------------------------------


def test_list_sites_empty(client):
    r = client.get("/api/sites")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sites_has_credential_count(client):
    make_site(
        client,
        name="Auth Site",
        requires_auth=True,
        login_url="https://auth.local/login",
        credentials=[{"username": "a", "password": "b"}],
    )
    r = client.get("/api/sites")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["credential_count"] == 1


def test_get_site(client):
    created = make_site(client).json()
    r = client.get(f"/api/sites/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_site_not_found(client):
    r = client.get("/api/sites/9999")
    assert r.status_code == 404


# ---- update -----------------------------------------------------------------


def test_update_site_replaces_credentials(client):
    created = make_site(
        client,
        name="Auth Site",
        requires_auth=True,
        login_url="https://auth.local/login",
        credentials=[{"username": "a", "password": "pass1"}],
    ).json()

    r = client.put(
        f"/api/sites/{created['id']}",
        json={
            "name": "Auth Site",
            "base_url": "https://auth.local",
            "requires_auth": True,
            "login_url": "https://auth.local/login",
            "credentials": [
                {"username": "x", "password": "px"},
                {"username": "y", "password": "py"},
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["credentials"]) == 2
    usernames = {c["username"] for c in data["credentials"]}
    assert usernames == {"x", "y"}


def test_update_site_not_found(client):
    r = client.put(
        "/api/sites/9999",
        json={"name": "x", "base_url": "https://x.local", "requires_auth": False},
    )
    assert r.status_code == 404


def test_update_duplicate_name(client):
    make_site(client, name="Alpha")
    b = make_site(client, name="Beta").json()
    r = client.put(
        f"/api/sites/{b['id']}",
        json={
            "name": "Alpha",
            "base_url": "https://beta.local",
            "requires_auth": False,
        },
    )
    assert r.status_code == 409


# ---- delete -----------------------------------------------------------------


def test_delete_site(client):
    created = make_site(client).json()
    r = client.delete(f"/api/sites/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/sites/{created['id']}").status_code == 404


def test_delete_cascades_credentials(client):
    site = make_site(
        client,
        name="Del Auth",
        requires_auth=True,
        login_url="https://del.local/login",
        credentials=[{"username": "u", "password": "p"}],
    ).json()
    cred_id = site["credentials"][0]["id"]
    client.delete(f"/api/sites/{site['id']}")
    # Credential endpoint should 404 now
    r = client.delete(f"/api/sites/{site['id']}/credentials/{cred_id}")
    assert r.status_code == 404


def test_delete_site_not_found(client):
    r = client.delete("/api/sites/9999")
    assert r.status_code == 404


# ---- individual credential endpoints ----------------------------------------


def test_add_credential(client):
    site = make_site(
        client,
        name="Auth Site",
        requires_auth=True,
        login_url="https://auth.local/login",
    ).json()
    r = client.post(
        f"/api/sites/{site['id']}/credentials",
        json={"username": "newuser", "password": "newpass", "label": "tester"},
    )
    assert r.status_code == 201
    assert r.json()["username"] == "newuser"


def test_add_credential_accepts_login_url(client):
    site = make_site(
        client,
        name="Auth Site",
        requires_auth=True,
        login_url="https://auth.local/login",
    ).json()
    r = client.post(
        f"/api/sites/{site['id']}/credentials",
        json={
            "username": "admin",
            "password": "newpass",
            "login_url": "https://auth.local/admin/login",
        },
    )

    assert r.status_code == 201
    assert r.json()["login_url"] == "https://auth.local/admin/login"


def test_add_credential_to_non_auth_site_rejected(client):
    site = make_site(client).json()
    r = client.post(
        f"/api/sites/{site['id']}/credentials",
        json={"username": "u", "password": "p"},
    )
    assert r.status_code == 400


def test_delete_credential(client):
    site = make_site(
        client,
        name="Auth Site",
        requires_auth=True,
        login_url="https://auth.local/login",
        credentials=[{"username": "u", "password": "p"}],
    ).json()
    cred_id = site["credentials"][0]["id"]
    r = client.delete(f"/api/sites/{site['id']}/credentials/{cred_id}")
    assert r.status_code == 204
    detail = client.get(f"/api/sites/{site['id']}").json()
    assert detail["credentials"] == []


def test_delete_credential_wrong_site(client):
    site_a = make_site(
        client,
        name="Site A",
        requires_auth=True,
        login_url="https://a.local/login",
        credentials=[{"username": "u", "password": "p"}],
    ).json()
    site_b = make_site(
        client,
        name="Site B",
        requires_auth=True,
        login_url="https://b.local/login",
    ).json()
    cred_id = site_a["credentials"][0]["id"]
    r = client.delete(f"/api/sites/{site_b['id']}/credentials/{cred_id}")
    assert r.status_code == 404
