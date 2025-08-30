"""
Test data fixtures for admin handlers tests.
"""
import datetime
from uuid import uuid4

import pytest

from portal.libs.consts.enums import Gender


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": uuid4(),
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "salt": "salt",
        "display_name": "Test User",
        "gender": Gender.UNKNOWN.value,
        "is_active": True,
        "is_superuser": False,
        "is_admin": True,
        "avatar_url": "https://example.com/avatar.jpg",
        "last_login_at": datetime.datetime.now(datetime.timezone.utc),
        "preferred_language": "zh-TW",
        "created_by": "test_admin",
        "updated_by": "test_admin"
    }


@pytest.fixture
def sample_admin_user_data():
    """Sample admin user data for testing."""
    return {
        "id": uuid4(),
        "email": "admin@example.com",
        "password_hash": "hashed_password",
        "salt": "salt",
        "display_name": "Admin User",
        "gender": Gender.UNKNOWN.value,
        "is_active": True,
        "is_superuser": True,
        "is_admin": True,
        "avatar_url": "https://example.com/admin_avatar.jpg",
        "last_login_at": datetime.datetime.now(datetime.timezone.utc),
        "preferred_language": "zh-TW",
        "created_by": "system",
        "updated_by": "system"
    }
