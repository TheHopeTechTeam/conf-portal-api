"""
Test admin auth handler
"""
import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pytest_mock import MockerFixture
from sqlalchemy import and_

from portal.handlers import AdminAuthHandler
from portal.libs.database.session_mock import SessionMock
from portal.models.rbac import PortalUser


@pytest.mark.asyncio
async def test_authenticate_admin_success(admin_auth_handler: AdminAuthHandler, sample_user_data: dict, mocker: MockerFixture):
    """Test successful admin authentication"""
    # Arrange
    email = sample_user_data["email"]
    password = "test_password"

    mock_user = {
        "id": sample_user_data["id"],
        "email": sample_user_data["email"],
        "password_hash": sample_user_data["password_hash"],
        "salt": sample_user_data["salt"],
        "is_admin": sample_user_data["is_admin"],
        "is_superuser": sample_user_data["is_superuser"],
        "status": sample_user_data["status"],
        "is_deleted": False
    }

    # Use SessionMock
    admin_auth_handler.session = SessionMock()
    admin_auth_handler.session.select(PortalUser).where(
            and_(
                PortalUser.email == email,
                PortalUser.is_deleted == False,
                PortalUser.is_active == True,
            )
        ).mock_fetchrow(mock_user)

    admin_auth_handler.password_provider.verify_password = mocker.Mock(return_value=True)  # type: Mock

    # Act
    result = await admin_auth_handler.authenticate_admin(email, password)

    # Assert
    assert result == mock_user
    admin_auth_handler.password_provider.verify_password.assert_called_once_with(
        password, mock_user["password_hash"]
    )


@pytest.mark.asyncio
async def test_authenticate_admin_superuser_success(admin_auth_handler: AdminAuthHandler, sample_admin_user_data, mocker):
    """Test successful superuser authentication"""
    # Arrange
    email = sample_admin_user_data["email"]
    password = "test_password"

    mock_user = {
        "id": sample_admin_user_data["id"],
        "email": sample_admin_user_data["email"],
        "password_hash": sample_admin_user_data["password_hash"],
        "salt": sample_admin_user_data["salt"],
        "is_admin": sample_admin_user_data["is_admin"],
        "is_superuser": sample_admin_user_data["is_superuser"],
        "status": sample_admin_user_data["status"],
        "is_deleted": False
    }

    admin_auth_handler.session = SessionMock()
    admin_auth_handler.session.select(PortalUser).where(
        and_(
            PortalUser.email == email,
            PortalUser.is_deleted == False,
            PortalUser.is_active == True,
        )
    ).mock_fetchrow(mock_user)

    admin_auth_handler.password_provider.verify_password = mocker.Mock(return_value=True)

    # Act
    result = await admin_auth_handler.authenticate_admin(email, password)

    # Assert
    assert result == mock_user
