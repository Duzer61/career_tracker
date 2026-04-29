"""Integration tests for authentication API endpoints."""

from tests.helpers import set_client_cookies


class TestRegister:
    """Tests for POST /api/auth/register."""

    REGISTER_URL = "/api/auth/register"

    async def test_register_success(self, client):
        """Should register a new user and return user data."""
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "newuser", "password": "StrongPass1"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["login"] == "newuser"
        assert "id" in data
        assert "password" not in data

    async def test_register_duplicate_login(self, client):
        """Should return 400 when registering with an existing login."""
        await client.post(
            self.REGISTER_URL,
            json={"login": "dupuser", "password": "StrongPass1"},
        )
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "dupuser", "password": "StrongPass1"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_password(self, client):
        """Should return 422 for a weak password."""
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "weakuser", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/auth/login."""

    LOGIN_URL = "/api/auth/login"
    REGISTER_URL = "/api/auth/register"

    async def _register_and_login(self, client, login="logintest", password="StrongPass1"):
        """Register a user and return login response."""
        await client.post(self.REGISTER_URL, json={"login": login, "password": password})
        return await client.post(self.LOGIN_URL, json={"login": login, "password": password})

    async def test_login_success(self, client):
        """Should login successfully and set cookies."""
        response = await self._register_and_login(client)
        assert response.status_code == 200
        assert response.json() == {"message": "login successful"}
        set_client_cookies(client, response)
        cookies = dict(response.cookies)
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    async def test_login_wrong_password(self, client):
        """Should return 401 for wrong password."""
        await client.post(self.REGISTER_URL, json={"login": "failuser", "password": "StrongPass1"})
        response = await client.post(
            self.LOGIN_URL, json={"login": "failuser", "password": "WrongPass1"}
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client):
        """Should return 401 for a user that doesn't exist."""
        response = await client.post(
            self.LOGIN_URL, json={"login": "nobody", "password": "SomePass1"}
        )
        assert response.status_code == 401


class TestRefresh:
    """Tests for POST /api/auth/refresh."""

    REFRESH_URL = "/api/auth/refresh"
    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"

    async def _login_and_get_cookies(self, client, login="refreshtest", password="StrongPass1"):
        """Register, login, and return response with cookies."""
        await client.post(self.REGISTER_URL, json={"login": login, "password": password})
        response = await client.post(self.LOGIN_URL, json={"login": login, "password": password})
        return response

    async def test_refresh_success(self, client):
        """Should refresh tokens and set new cookies."""
        login_resp = await self._login_and_get_cookies(client)
        set_client_cookies(client, login_resp)
        login_cookies = dict(login_resp.cookies)

        response = await client.post(
            self.REFRESH_URL,
            headers={"Cookie": f"refresh_token={login_cookies['refresh_token']}"},
        )
        assert response.status_code == 200
        assert "Tokens refreshed" in response.json()["message"]
        refresh_cookies = dict(response.cookies)
        assert "access_token" in refresh_cookies
        assert "refresh_token" in refresh_cookies

    async def test_refresh_no_token(self, client):
        """Should return 401 when no refresh token cookie is sent."""
        response = await client.post(self.REFRESH_URL)
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout and logout-all."""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"
    LOGOUT_URL = "/api/auth/logout"
    LOGOUT_ALL_URL = "/api/auth/logout-all"

    async def test_logout_success(self, client):
        """Should logout and delete cookies."""
        await client.post(
            self.REGISTER_URL, json={"login": "logoutuser", "password": "StrongPass1"}
        )
        login_resp = await client.post(
            self.LOGIN_URL, json={"login": "logoutuser", "password": "StrongPass1"}
        )
        set_client_cookies(client, login_resp)

        response = await client.post(self.LOGOUT_URL)
        assert response.status_code == 200
        assert response.json() == {"message": "logout successful"}

    async def test_logout_all_success(self, client):
        """Should logout from all devices and delete cookies."""
        await client.post(
            self.REGISTER_URL, json={"login": "logoutalluser", "password": "StrongPass1"}
        )
        login_resp = await client.post(
            self.LOGIN_URL, json={"login": "logoutalluser", "password": "StrongPass1"}
        )
        set_client_cookies(client, login_resp)

        response = await client.post(self.LOGOUT_ALL_URL)
        assert response.status_code == 200
        assert response.json() == {"message": "Logged out from all devices"}
