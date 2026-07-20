"""Integration tests for authentication API endpoints."""

import pytest

from tests.helpers import set_client_cookies


class TestRegister:
    """Tests for POST /api/auth/register."""

    REGISTER_URL = "/api/auth/register"

    async def test_register_success(self, client):
        """Should register a new user, set cookies, and return user data with message."""
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "newuser", "password": "StrongPass1", "password_confirm": "StrongPass1"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["login"] == "newuser"
        assert "id" in data
        assert "password" not in data
        assert data["message"] == "Регистрация прошла успешно"

        # Check that cookies are set (auto-login)
        cookies = dict(response.cookies)
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    async def test_register_duplicate_login(self, client):
        """Should return 400 when registering with an existing login."""
        await client.post(
            self.REGISTER_URL,
            json={"login": "dupuser", "password": "StrongPass1", "password_confirm": "StrongPass1"},
        )
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "dupuser", "password": "StrongPass1", "password_confirm": "StrongPass1"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_password(self, client):
        """Should return 422 for a weak password."""
        response = await client.post(
            self.REGISTER_URL,
            json={"login": "weakuser", "password": "short", "password_confirm": "short"},
        )
        assert response.status_code == 422

    async def test_register_password_mismatch(self, client):
        """Should return 422 when password and password_confirm do not match."""
        response = await client.post(
            self.REGISTER_URL,
            json={
                "login": "mismatchuser",
                "password": "StrongPass1",
                "password_confirm": "DifferentPass1",
            },
        )
        assert response.status_code == 422
        assert "Пароли не совпадают" in response.text


class TestLogin:
    """Tests for POST /api/auth/login."""

    LOGIN_URL = "/api/auth/login"
    REGISTER_URL = "/api/auth/register"

    async def _register_and_login(self, client, login="logintest", password="StrongPass1"):
        """Register a user and return login response."""
        await client.post(
            self.REGISTER_URL,
            json={"login": login, "password": password, "password_confirm": password},
        )
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
        await client.post(
            self.REGISTER_URL,
            json={
                "login": "failuser",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
        )
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
        await client.post(
            self.REGISTER_URL,
            json={"login": login, "password": password, "password_confirm": password},
        )
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
            self.REGISTER_URL,
            json={
                "login": "logoutuser",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
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
            self.REGISTER_URL,
            json={
                "login": "logoutalluser",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
        )
        login_resp = await client.post(
            self.LOGIN_URL, json={"login": "logoutalluser", "password": "StrongPass1"}
        )
        set_client_cookies(client, login_resp)

        response = await client.post(self.LOGOUT_ALL_URL)
        assert response.status_code == 200
        assert response.json() == {"message": "Logged out from all devices"}


class TestSuperAdmin:
    """Tests for superadmin functionality via user API endpoints."""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Override config to set SUPERADMIN_LOGIN for this test class."""
        from app.config import config

        self._orig_superadmin = config.SUPERADMIN_LOGIN
        config.SUPERADMIN_LOGIN = "superadmin"
        yield
        config.SUPERADMIN_LOGIN = self._orig_superadmin

    async def _create_user_and_login(self, client, login: str, password="StrongPass1"):
        """Register a user and return client with cookies set."""
        await client.post(
            self.REGISTER_URL,
            json={"login": login, "password": password, "password_confirm": password},
        )
        resp = await client.post(self.LOGIN_URL, json={"login": login, "password": password})
        set_client_cookies(client, resp)
        return resp

    async def test_get_me_returns_is_superadmin_for_superadmin(self, client):
        """Should return is_superadmin=true for the user matching SUPERADMIN_LOGIN."""
        await self._create_user_and_login(client, "superadmin")
        response = await client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["is_superadmin"] is True
        assert data["is_admin"] is False  # superadmin without explicit admin flag

    async def test_get_me_returns_is_superadmin_false_for_regular_user(self, client):
        """Should return is_superadmin=false for a regular user."""
        await self._create_user_and_login(client, "regularuser")
        response = await client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data.get("is_superadmin") is False

    async def test_superadmin_cannot_delete_self(self, client):
        """Superadmin should get 403 when trying to delete own account."""
        await self._create_user_and_login(client, "superadmin")
        response = await client.delete("/api/users/me")
        assert response.status_code == 403
        assert "protected" in response.json()["detail"].lower()

    async def test_toggle_admin_status_by_non_superadmin_returns_403(self, client):
        """Regular admin should get 403 when trying to toggle admin status."""
        # Register and login as a regular admin
        await self._create_user_and_login(client, "regularuser")
        response = await client.patch(
            "/api/users/1/admin",
            json={"is_admin": True},
        )
        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]

    async def test_superadmin_can_toggle_admin_status(self, client, test_session):
        """Superadmin should be able to set/unset admin status for another user."""
        # Create superadmin user and target user
        await client.post(
            self.REGISTER_URL,
            json={
                "login": "superadmin",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
        )
        await client.post(
            self.REGISTER_URL,
            json={
                "login": "targetuser",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
        )

        # Login as superadmin
        await self._create_user_and_login(client, "superadmin")

        # Get target user by listing users
        list_resp = await client.get("/api/users")
        assert list_resp.status_code == 200
        users = list_resp.json()["items"]
        target = [u for u in users if u["login"] == "targetuser"][0]
        target_id = target["id"]

        # Toggle admin ON
        resp_on = await client.patch(
            f"/api/users/{target_id}/admin",
            json={"is_admin": True},
        )
        assert resp_on.status_code == 200
        assert resp_on.json()["is_admin"] is True

        # Toggle admin OFF
        resp_off = await client.patch(
            f"/api/users/{target_id}/admin",
            json={"is_admin": False},
        )
        assert resp_off.status_code == 200
        assert resp_off.json()["is_admin"] is False

    async def test_superadmin_without_admin_flag_can_access_admin_page(self, client):
        """Superadmin with is_admin=False should still be able to access admin endpoints."""
        await self._create_user_and_login(client, "superadmin")
        # The user is superadmin but not admin — should still access /api/users
        response = await client.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)


class TestChangePassword:
    """Tests for POST /api/auth/change-password."""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"
    CHANGE_URL = "/api/auth/change-password"
    ME_URL = "/api/users/me"

    async def _register_and_login(self, client, login="changepwuser", password="StrongPass1"):
        """Register, login and set client cookies."""
        await client.post(
            self.REGISTER_URL,
            json={"login": login, "password": password, "password_confirm": password},
        )
        resp = await client.post(self.LOGIN_URL, json={"login": login, "password": password})
        set_client_cookies(client, resp)
        return resp

    async def test_change_password_success(self, client):
        """Should change password successfully and keep current session alive."""
        await self._register_and_login(client)
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "NewStrongPass1",
                "new_password_confirm": "NewStrongPass1",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Пароль успешно изменён"

        # New cookies should be set (session re-issued)
        cookies = dict(response.cookies)
        assert "access_token" in cookies
        assert "refresh_token" in cookies

        # Current session should still work — can access /api/users/me
        resp = await client.get(self.ME_URL)
        assert resp.status_code == 200
        assert resp.json()["login"] == "changepwuser"

        # Old password should no longer work
        await client.post(self.LOGIN_URL, json={"login": "changepwuser", "password": "StrongPass1"})
        # Login with new password should work
        resp2 = await client.post(
            self.LOGIN_URL, json={"login": "changepwuser", "password": "NewStrongPass1"}
        )
        assert resp2.status_code == 200

    async def test_change_password_wrong_old_password(self, client):
        """Should return 400 when old password is incorrect."""
        await self._register_and_login(client)
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "WrongOldPass1",
                "new_password": "NewStrongPass1",
                "new_password_confirm": "NewStrongPass1",
            },
        )
        assert response.status_code == 400
        assert "Неверный старый пароль" in response.json()["detail"]

    async def test_change_password_weak_new_password(self, client):
        """Should return 422 when new password is too weak."""
        await self._register_and_login(client)
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "weak",
                "new_password_confirm": "weak",
            },
        )
        assert response.status_code == 422

    async def test_change_password_mismatch(self, client):
        """Should return 422 when new passwords do not match."""
        await self._register_and_login(client)
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "NewStrongPass1",
                "new_password_confirm": "DifferentPass1",
            },
        )
        assert response.status_code == 422
        assert "Новые пароли не совпадают" in response.text

    async def test_change_password_same_as_old(self, client):
        """Should return 422 when new password is same as old."""
        await self._register_and_login(client)
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "StrongPass1",
                "new_password_confirm": "StrongPass1",
            },
        )
        assert response.status_code == 422
        assert "должен отличаться" in response.text

    async def test_change_password_requires_auth(self, client):
        """Should return 401 when not authenticated."""
        response = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "NewStrongPass1",
                "new_password_confirm": "NewStrongPass1",
            },
        )
        assert response.status_code == 401

    async def test_change_password_revokes_other_sessions(self, client):
        """Should revoke other sessions — only current session stays valid."""
        # Register user
        await client.post(
            self.REGISTER_URL,
            json={
                "login": "changepwuser",
                "password": "StrongPass1",
                "password_confirm": "StrongPass1",
            },
        )

        # First login — captures session A cookies
        login_a_resp = await client.post(
            self.LOGIN_URL, json={"login": "changepwuser", "password": "StrongPass1"}
        )
        cookies_session_a = dict(login_a_resp.cookies)

        # Second login — session B becomes current
        login_b_resp = await client.post(
            self.LOGIN_URL, json={"login": "changepwuser", "password": "StrongPass1"}
        )
        set_client_cookies(client, login_b_resp)

        # Change password — session A should be revoked, session B stays
        resp = await client.post(
            self.CHANGE_URL,
            json={
                "old_password": "StrongPass1",
                "new_password": "NewStrongPass1",
                "new_password_confirm": "NewStrongPass1",
            },
        )
        assert resp.status_code == 200
        set_client_cookies(client, resp)

        # Session A (old tokens) should be revoked
        # Clear client cookies so only the manually set header is sent
        client.cookies.clear()
        response = await client.get(
            self.ME_URL,
            headers={
                "Cookie": (
                    f"access_token={cookies_session_a.get('access_token', '')}; "
                    f"refresh_token={cookies_session_a.get('refresh_token', '')}"
                )
            },
        )
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()

        # Current session (B) should still work
        set_client_cookies(client, resp)
        resp_me = await client.get(self.ME_URL)
        assert resp_me.status_code == 200
        assert resp_me.json()["login"] == "changepwuser"
