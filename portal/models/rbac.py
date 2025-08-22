"""
Model of the user table
"""
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from portal.libs.consts.enums import Gender
from portal.libs.database.orm import ModelBase
from .mixins import AuditMixin, DeletedMixin, RemarkMixin, DescriptionMixin, BaseMixin
from .relationships import portal_user_role, portal_role_permission


class PortalUser(ModelBase, RemarkMixin, DeletedMixin, AuditMixin):
    """Portal User Model"""
    phone_number = Column(
        sa.String(16),
        nullable=False,
        unique=True,
        comment="Phone number, unique identifier"
    )
    email = Column(sa.String(64), nullable=True, unique=True, comment="Email, unique identifier")
    password_hash = Column(sa.String(512), nullable=True, comment="Password hash")
    salt = Column(sa.String(128), nullable=True, comment="Salt for password hash")
    is_active = Column(sa.Boolean, default=True, comment="Is active")
    verified = Column(sa.Boolean, default=False, comment="Is verified")
    last_login_at = Column(sa.TIMESTAMP(timezone=True), comment="Last login")
    password_changed_at = Column(sa.TIMESTAMP(timezone=True), comment="Password last changed time")
    password_expires_at = Column(sa.TIMESTAMP(timezone=True), comment="Password expiration time")
    is_superuser = Column(sa.Boolean, default=False, comment="Is superuser")
    is_admin = Column(sa.Boolean, default=False, comment="Is admin")

    # Relationships
    roles = relationship("PortalRole", secondary=lambda: portal_user_role, back_populates="users", passive_deletes=True)


class PortalUserProfile(ModelBase, DeletedMixin, AuditMixin, DescriptionMixin):
    """Portal User Profile Model"""
    user_id = Column(
        UUID,
        sa.ForeignKey(PortalUser.id, ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="User ID",
        index=True
    )
    display_name = Column(sa.String(64), comment="Display name")
    gender = Column(sa.Integer, default=Gender.UNKNOWN.value, comment="Refer to Gender enum")


class PortalThirdPartyProvider(ModelBase, DeletedMixin, AuditMixin, RemarkMixin):
    """Portal Third Party Provider Model"""
    name = Column(sa.String(16), nullable=False, unique=True, comment="Provider name, Enum: Provider")


class PortalUserThirdPartyAuth(ModelBase, DeletedMixin, AuditMixin):
    """Portal User Third Party Auth Model"""
    __extra_table_args__ = (
        sa.UniqueConstraint("user_id", "provider_id"),
    )
    user_id = Column(
        UUID,
        sa.ForeignKey(PortalUser.id, ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
        index=True
    )
    provider_id = Column(
        UUID,
        sa.ForeignKey(PortalThirdPartyProvider.id, ondelete="CASCADE"),
        nullable=False,
        comment="Provider ID"
    )
    access_token = Column(sa.String(255), comment="Access token")
    refresh_token = Column(sa.String(255), comment="Refresh token")
    token_expires_at = Column(sa.TIMESTAMP(timezone=True), comment="Token expiration time")
    additional_data = Column(JSONB, comment="Additional data")


class PortalRole(ModelBase, BaseMixin):
    """Portal Role Model for RBAC"""
    code = Column(sa.String(32), nullable=False, unique=True, comment="Role code")
    name = Column(sa.String(64), comment="Role name")
    is_active = Column(sa.Boolean, default=True, comment="Is role active")
    # Relationships
    users = relationship("PortalUser", secondary=lambda: portal_user_role, back_populates="roles", passive_deletes=True)
    permissions = relationship("PortalPermission", secondary=lambda: portal_role_permission, back_populates="roles", passive_deletes=True)


class PortalResource(ModelBase, BaseMixin):
    """Portal Resource Model for RBAC"""
    code = Column(sa.String(32), nullable=False, unique=True, comment="Resource code (e.g., user, course, article)")
    name = Column(sa.String(64), comment="Resource name")
    is_active = Column(sa.Boolean, default=True, comment="Is resource active")


class PortalVerb(ModelBase, BaseMixin):
    """Portal Verb Model for RBAC"""
    action = Column(sa.String(32), nullable=False, unique=True, comment="Verb action (e.g., create, read, update, delete)")
    display_name = Column(sa.String(64), comment="Display name")
    is_active = Column(sa.Boolean, default=True, comment="Is verb active")


class PortalPermission(ModelBase, BaseMixin):
    """Portal Permission Model for RBAC"""
    __extra_table_args__ = (
        sa.UniqueConstraint("resource_id", "verb_id"),
    )
    resource_id = Column(UUID, sa.ForeignKey(PortalResource.id, ondelete="CASCADE"), nullable=False, comment="Resource ID")
    verb_id = Column(UUID, sa.ForeignKey(PortalVerb.id, ondelete="CASCADE"), nullable=False, comment="Verb ID")
    code = Column(sa.String(128), nullable=False, comment="Permission Code (e.g., user:read)")
    display_name = Column(sa.String(128), comment="Display name")
    expire_date = Column(sa.DateTime(timezone=True), comment="Expiration time, can be used for temporary authorization")
    is_active = Column(sa.Boolean, default=True, comment="Is permission active")

    # Relationships
    roles = relationship("PortalRole", secondary=lambda: portal_role_permission, back_populates="permissions", passive_deletes=True)
