"""Tests for CRUD operations (direct DB calls)."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.auth import get_password_hash
from app.crud import (
    auto_ignore_old_applications,
    create_application,
    create_user,
    delete_application,
    get_application,
    get_applications,
    update_application,
)
from app.db.models import ApplicationStatus, User
from app.schemas import ApplicationCreate, ApplicationUpdate, UserCreate
from app.utils import utc_now


class TestUserCRUD:
    """Tests for user CRUD operations."""

    async def test_create_user(self, test_session):
        """Should create a user and return it."""
        user_data = UserCreate(login="newuser", password="StrongPass1")
        user = await create_user(test_session, user_data)
        assert user.login == "newuser"
        assert user.id is not None

    async def test_create_duplicate_user(self, test_session):
        """Should raise on duplicate login."""
        user_data = UserCreate(login="dupuser", password="StrongPass1")
        await create_user(test_session, user_data)
        with pytest.raises(ValueError, match="already exists"):
            await create_user(test_session, user_data)


class TestApplicationCRUD:
    """Tests for application CRUD operations."""

    async def test_get_applications_empty(self, test_session, test_user):
        """Should return empty list for new user."""
        apps = await get_applications(test_session, False, test_user)
        assert apps == []

    async def test_create_application(self, test_session, test_user):
        """Should create an application and return it."""
        app_data = ApplicationCreate(company_name="Test Corp", vacancy_name="Python Dev")
        app = await create_application(app_data, test_session, test_user)
        assert app.company_name == "Test Corp"
        assert app.vacancy_name == "Python Dev"
        assert app.status == ApplicationStatus.CREATED
        assert app.user_id == test_user.id
        assert app.id is not None

    async def test_get_applications_returns_user_apps(self, test_session, test_user):
        """Should return only the user's applications."""
        await create_application(
            ApplicationCreate(company_name="App 1", vacancy_name="Vacancy 1"),
            test_session,
            test_user,
        )
        await create_application(
            ApplicationCreate(company_name="App 2", vacancy_name="Vacancy 2"),
            test_session,
            test_user,
        )

        apps = await get_applications(test_session, False, test_user)
        assert len(apps) == 2

    async def test_get_applications_ordering(self, test_session, test_user):
        """Should return applications ordered correctly based on reverse flag."""
        import asyncio

        app1 = await create_application(
            ApplicationCreate(company_name="First", vacancy_name="Vacancy 1"),
            test_session,
            test_user,
        )
        await asyncio.sleep(0.01)
        app2 = await create_application(
            ApplicationCreate(company_name="Second", vacancy_name="Vacancy 2"),
            test_session,
            test_user,
        )
        await asyncio.sleep(0.01)
        app3 = await create_application(
            ApplicationCreate(company_name="Third", vacancy_name="Vacancy 3"),
            test_session,
            test_user,
        )

        # reverse=False (default) → DESC: newest first
        apps_desc = await get_applications(test_session, False, test_user)
        assert [a.id for a in apps_desc] == [app3.id, app2.id, app1.id]

        # reverse=True → ASC: oldest first
        apps_asc = await get_applications(test_session, True, test_user)
        assert [a.id for a in apps_asc] == [app1.id, app2.id, app3.id]

    async def test_get_application_by_id(self, test_session, test_user):
        """Should return a specific application by ID."""
        created = await create_application(
            ApplicationCreate(company_name="Target Corp", vacancy_name="Target Role"),
            test_session,
            test_user,
        )
        fetched = await get_application(created.id, test_session, test_user)
        assert fetched.company_name == "Target Corp"
        assert fetched.vacancy_name == "Target Role"
        assert fetched.user_id == test_user.id

    async def test_get_application_not_found(self, test_session, test_user):
        """Should return None for non-existent ID."""
        with pytest.raises(HTTPException):
            await get_application(9999, test_session, test_user)

    async def test_update_application(self, test_session, test_user):
        """Should update application fields."""
        created = await create_application(
            ApplicationCreate(company_name="Old Corp", vacancy_name="Old Role"),
            test_session,
            test_user,
        )
        updated = await update_application(
            created.id,
            ApplicationUpdate(company_name="Updated Corp", contacts="new@test.com"),
            test_session,
            test_user,
        )
        assert updated.company_name == "Updated Corp"
        assert updated.contacts == "new@test.com"
        assert updated.vacancy_name == "Old Role"  # not updated, remain unchanged

    async def test_update_application_status(self, test_session, test_user):
        """Should update application status."""
        created = await create_application(
            ApplicationCreate(company_name="Status Corp", vacancy_name="Status Role"),
            test_session,
            test_user,
        )
        updated = await update_application(
            created.id,
            ApplicationUpdate(status="offer"),
            test_session,
            test_user,
        )
        assert updated.status.value == "offer"

    async def test_delete_application(self, test_session, test_user):
        """Should delete an application."""
        created = await create_application(
            ApplicationCreate(company_name="Delete Corp", vacancy_name="Delete Role"),
            test_session,
            test_user,
        )
        await delete_application(created.id, test_session, test_user)

        with pytest.raises(HTTPException):
            await get_application(created.id, test_session, test_user)

    async def test_isolation_between_users(self, test_session, test_user):
        """Should not leak applications between users."""
        await create_application(
            ApplicationCreate(company_name="User1 App", vacancy_name="User1 Role"),
            test_session,
            test_user,
        )
        # Create another user and check their list is empty
        other = User(login="otheruser", hashed_password=get_password_hash("StrongPass1"))
        test_session.add(other)
        await test_session.commit()
        await test_session.refresh(other)

        apps = await get_applications(test_session, False, other)
        assert apps == []

    # ── Auto-Ignore ───────────────────────────

    async def test_auto_ignore_old_created_applications(self, test_session, test_user):
        """Should ignore CREATED applications older than the specified days."""
        # Create old CREATED application (> 30 days)
        old_app = await create_application(
            ApplicationCreate(company_name="Old Corp", vacancy_name="Old Role"),
            test_session,
            test_user,
        )
        old_app.created_at = utc_now() - timedelta(days=31)

        # Create recent CREATED application
        recent_app = await create_application(
            ApplicationCreate(company_name="Recent Corp", vacancy_name="Recent Role"),
            test_session,
            test_user,
        )

        # Create old non-CREATED application
        offer_app = await create_application(
            ApplicationCreate(company_name="Offer Corp", vacancy_name="Offer Role"),
            test_session,
            test_user,
        )
        await test_session.refresh(offer_app)
        offer_app.created_at = utc_now() - timedelta(days=31)
        offer_app.status = ApplicationStatus.OFFER

        await test_session.commit()

        ignored = await auto_ignore_old_applications(test_session, test_user, 30)
        assert ignored == 1

        # Refresh and check statuses
        await test_session.refresh(old_app)
        assert old_app.status == ApplicationStatus.IGNORED

        await test_session.refresh(recent_app)
        assert recent_app.status == ApplicationStatus.CREATED

        await test_session.refresh(offer_app)
        assert offer_app.status == ApplicationStatus.OFFER

    async def test_auto_ignore_strictly_older_check(self, test_session, test_user):
        """Should not ignore recently created applications (not strictly older)."""
        recent_app = await create_application(
            ApplicationCreate(company_name="Recent Corp", vacancy_name="Recent Role"),
            test_session,
            test_user,
        )
        # Don't touch created_at — it's "now"

        ignored = await auto_ignore_old_applications(test_session, test_user, 30)
        assert ignored == 0

        await test_session.refresh(recent_app)
        assert recent_app.status == ApplicationStatus.CREATED

    async def test_auto_ignore_no_applications(self, test_session, test_user):
        """Should return 0 when there are no old CREATED applications."""
        ignored = await auto_ignore_old_applications(test_session, test_user, 30)
        assert ignored == 0
