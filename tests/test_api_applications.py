"""Integration tests for Applications API endpoints."""

from tests.helpers import cookies_from_response


class TestApplicationsAPI:
    """Tests for CRUD operations on /api/applications."""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"
    APP_URL = "/api/applications"

    async def _setup_user(self, client):
        """Register and login a test user."""
        await client.post(
            self.REGISTER_URL,
            json={"login": "apptestuser", "password": "StrongPass1"},
        )
        login_resp = await client.post(
            self.LOGIN_URL,
            json={"login": "apptestuser", "password": "StrongPass1"},
        )
        return cookies_from_response(login_resp)

    async def _create_app(self, client, cookies, company_name="Test Corp", **kwargs):
        """Helper to create an application."""
        payload = {"company_name": company_name, **kwargs}
        return await client.post(self.APP_URL, json=payload, cookies=cookies)

    # ── List ──────────────────────────────────

    async def test_list_applications_empty(self, client):
        """Should return empty list for new user."""
        cookies = await self._setup_user(client)
        response = await client.get(self.APP_URL, cookies=cookies)
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_applications(self, client):
        """Should return all user applications."""
        cookies = await self._setup_user(client)
        await self._create_app(client, cookies, "First Corp")
        await self._create_app(client, cookies, "Second Corp")

        response = await client.get(self.APP_URL, cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    # ── Create ────────────────────────────────

    async def test_create_application(self, client):
        """Should create an application and return it."""
        cookies = await self._setup_user(client)
        response = await self._create_app(
            client,
            cookies,
            company_name="New Corp",
            contacts="hr@new.com",
            comments="Interesting position",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "New Corp"
        assert data["contacts"] == "hr@new.com"
        assert data["status"] == "created"
        assert "id" in data
        assert "created_at" in data

    async def test_create_application_minimal(self, client):
        """Should create an application with only company_name."""
        cookies = await self._setup_user(client)
        response = await self._create_app(client, cookies, company_name="Minimal Corp")
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Minimal Corp"

    async def test_create_application_empty_name(self, client):
        """Should return 422 for empty company name."""
        cookies = await self._setup_user(client)
        response = await self._create_app(client, cookies, company_name="")
        assert response.status_code == 422

    # ── Get by ID ─────────────────────────────

    async def test_get_application_by_id(self, client):
        """Should return a specific application by ID."""
        cookies = await self._setup_user(client)
        created = await self._create_app(client, cookies, "Target Corp")
        app_id = created.json()["id"]

        response = await client.get(f"{self.APP_URL}/{app_id}", cookies=cookies)
        assert response.status_code == 200
        assert response.json()["company_name"] == "Target Corp"

    async def test_get_application_not_found(self, client):
        """Should return 404 for non-existent application."""
        cookies = await self._setup_user(client)
        response = await client.get(f"{self.APP_URL}/9999", cookies=cookies)
        assert response.status_code == 404

    # ── Update ────────────────────────────────

    async def test_update_application(self, client):
        """Should update application fields."""
        cookies = await self._setup_user(client)
        created = await self._create_app(client, cookies, "Old Corp")
        app_id = created.json()["id"]

        response = await client.patch(
            f"{self.APP_URL}/{app_id}",
            json={"company_name": "Updated Corp", "contacts": "updated@test.com"},
            cookies=cookies,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Updated Corp"
        assert data["contacts"] == "updated@test.com"

    async def test_update_application_status(self, client):
        """Should update application status."""
        cookies = await self._setup_user(client)
        created = await self._create_app(client, cookies, "Status Corp")
        app_id = created.json()["id"]

        response = await client.patch(
            f"{self.APP_URL}/{app_id}",
            json={"status": "offer"},
            cookies=cookies,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "offer"

    async def test_update_application_not_found(self, client):
        """Should return 404 when updating non-existent app."""
        cookies = await self._setup_user(client)
        response = await client.patch(
            f"{self.APP_URL}/9999",
            json={"company_name": "Nope"},
            cookies=cookies,
        )
        assert response.status_code == 404

    # ── Delete ────────────────────────────────

    async def test_delete_application(self, client):
        """Should delete an application."""
        cookies = await self._setup_user(client)
        created = await self._create_app(client, cookies, "Delete Corp")
        app_id = created.json()["id"]

        response = await client.delete(f"{self.APP_URL}/{app_id}", cookies=cookies)
        assert response.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"{self.APP_URL}/{app_id}", cookies=cookies)
        assert get_resp.status_code == 404

    async def test_delete_application_not_found(self, client):
        """Should return 404 when deleting non-existent app."""
        cookies = await self._setup_user(client)
        response = await client.delete(f"{self.APP_URL}/9999", cookies=cookies)
        assert response.status_code == 404

    # ── Authentication checks ─────────────────

    async def test_unauthorized_access(self, client):
        """Should return 401 without auth cookies."""
        response = await client.get(self.APP_URL)
        assert response.status_code == 401

        response = await client.post(self.APP_URL, json={"company_name": "Hacker Corp"})
        assert response.status_code == 401

        response = await client.delete(f"{self.APP_URL}/1")
        assert response.status_code == 401
