"""Tests for Pydantic schemas: validation, serialization, and parsing."""

import pytest
from pydantic import ValidationError

from app.schemas import ApplicationCreate, ApplicationUpdate, UserCreate, UserLogin


class TestUserCreate:
    """Tests for UserCreate schema validation."""

    def test_valid_password(self):
        """Should accept a password meeting all requirements."""
        user = UserCreate(login="user1", password="ValidPass123", password_confirm="ValidPass123")
        assert user.login == "user1"
        assert user.password == "ValidPass123"

    def test_password_too_short(self):
        """Should reject password shorter than 8 characters."""
        with pytest.raises(ValidationError, match="минимум 8 символов"):
            UserCreate(login="user1", password="Ab1", password_confirm="Ab1")

    def test_password_missing_lowercase(self):
        """Should reject password without lowercase letters."""
        with pytest.raises(ValidationError, match="строчную букву"):
            UserCreate(login="user1", password="UPPERCASE123", password_confirm="UPPERCASE123")

    def test_password_missing_uppercase(self):
        """Should reject password without uppercase letters."""
        with pytest.raises(ValidationError, match="заглавную букву"):
            UserCreate(login="user1", password="lowercase123", password_confirm="lowercase123")

    def test_password_missing_digit(self):
        """Should reject password without digits."""
        with pytest.raises(ValidationError, match="цифру"):
            UserCreate(login="user1", password="NoDigitsHere", password_confirm="NoDigitsHere")

    def test_password_invalid_characters(self):
        """Should reject password with non-ASCII characters."""
        with pytest.raises(ValidationError, match="ASCII"):
            UserCreate(login="user1", password="русскийПароль1", password_confirm="русскийПароль1")

    def test_passwords_do_not_match(self):
        """Should reject when password and password_confirm differ."""
        with pytest.raises(ValidationError, match="Пароли не совпадают"):
            UserCreate(login="user1", password="ValidPass123", password_confirm="DifferentPass1")


class TestUserLogin:
    """Tests for UserLogin schema."""

    def test_valid_login_data(self):
        """Should accept valid login credentials."""
        data = UserLogin(login="user1", password="mypassword")
        assert data.login == "user1"
        assert data.password == "mypassword"


class TestApplicationCreate:
    """Tests for ApplicationCreate schema."""

    def test_valid_application(self):
        """Should accept a minimal valid application."""
        app = ApplicationCreate(company_name="Test Corp", vacancy_name="Python Developer")
        assert app.company_name == "Test Corp"
        assert app.vacancy_name == "Python Developer"
        assert app.contacts is None
        assert app.comments is None
        assert app.vacancy_url is None

    def test_valid_application_full(self):
        """Should accept an application with all optional fields."""
        app = ApplicationCreate(
            company_name="Test Corp",
            vacancy_name="Python Developer",
            contacts="hr@test.com",
            comments="Applied via LinkedIn",
            vacancy_url="https://test.com/job/123",
        )
        assert app.company_name == "Test Corp"
        assert app.vacancy_name == "Python Developer"
        assert app.contacts == "hr@test.com"

    def test_empty_company_name(self):
        """Should reject empty company name."""
        with pytest.raises(ValidationError):
            ApplicationCreate(company_name="", vacancy_name="Python Developer")

    def test_company_name_too_long(self):
        """Should reject company name exceeding 255 characters."""
        with pytest.raises(ValidationError):
            ApplicationCreate(company_name="A" * 256, vacancy_name="Python Developer")


class TestApplicationUpdate:
    """Tests for ApplicationUpdate schema."""

    def test_partial_update(self):
        """Should allow updating only some fields."""
        data = ApplicationUpdate(company_name="New Corp")
        assert data.company_name == "New Corp"
        assert data.status is None
        assert data.contacts is None

    def test_update_all_fields(self):
        """Should allow updating all fields simultaneously."""
        data = ApplicationUpdate(
            company_name="New Corp",
            vacancy_name="Senior Python Developer",
            status="offer",
            contacts="new@test.com",
            comments="Updated",
            vacancy_url="https://test.com/new",
        )
        assert data.status == "offer"
        assert data.vacancy_name == "Senior Python Developer"
