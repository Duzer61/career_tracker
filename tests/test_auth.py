"""Tests for auth utilities (password hashing, JWT tokens)."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.auth import (
    create_jwt_token,
    get_password_hash,
    verify_password,
)
from app.config import config as cf

# ──────────────────────────────────────────────
# Password hashing
# ──────────────────────────────────────────────


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_and_verify(self):
        """Should hash and verify a correct password."""
        password = "StrongPass1"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        """Should not verify a wrong password."""
        hashed = get_password_hash("StrongPass1")
        assert not verify_password("WrongPass1", hashed)

    def test_different_hashes(self):
        """Should produce different hashes for the same password (due to salt)."""
        hashed1 = get_password_hash("StrongPass1")
        hashed2 = get_password_hash("StrongPass1")
        assert hashed1 != hashed2


# ──────────────────────────────────────────────
# JWT token creation and decoding
# ──────────────────────────────────────────────


class TestJWTToken:
    """Tests for JWT token creation and decoding."""

    def test_create_and_decode_access_token(self):
        """Should create and decode an access token."""
        payload = {"sub": "testuser", "token_type": "access"}
        token = create_jwt_token(payload)
        decoded = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert decoded["token_type"] == "access"

    def test_create_and_decode_refresh_token(self):
        """Should create and decode a refresh token."""
        payload = {"sub": "testuser", "token_type": "refresh"}
        token = create_jwt_token(payload)
        decoded = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert decoded["token_type"] == "refresh"

    def test_token_expiration(self):
        """Should set default expiration on token."""
        payload = {"sub": "testuser"}
        token = create_jwt_token(payload)
        decoded = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        assert "exp" in decoded

    def test_token_with_custom_expiration(self):
        """Should respect custom expiration delta."""
        payload = {"sub": "testuser"}
        token = create_jwt_token(payload=payload, expires_delta=timedelta(seconds=60))

        decoded = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        exp = decoded["exp"]
        expected = datetime.now(timezone.utc) + timedelta(seconds=60)
        assert abs(exp - expected.timestamp()) < 2

    def test_decode_invalid_token(self):
        """Should raise on invalid token."""
        with pytest.raises(Exception):
            jwt.decode("invalid.token.here", cf.SECRET_KEY, algorithms=[cf.ALGORITHM])

    def test_decode_expired_token(self):
        """Should raise on expired token."""
        payload = {"sub": "testuser"}
        token = create_jwt_token(payload=payload, expires_delta=timedelta(seconds=-60))
        with pytest.raises(Exception):
            jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])

    def test_token_with_wrong_secret(self):
        """Should raise when decoding with wrong secret."""
        payload = {"sub": "testuser"}
        token = create_jwt_token(payload)
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret", algorithms=[cf.ALGORITHM])
