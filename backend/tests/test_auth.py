"""Tests for authentication endpoints."""


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "newuser"

    def test_register_duplicate(self, client):
        client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "password456",
        })
        assert resp.status_code == 400

    def test_register_short_username(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "ab",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "password": "short",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", data={
            "username": "loginuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "username": "loginuser2",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", data={
            "username": "loginuser2",
            "password": "wrongpass123",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", data={
            "username": "noexist",
            "password": "password123",
        })
        assert resp.status_code == 401


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_me_no_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
