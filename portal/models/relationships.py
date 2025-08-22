"""
Relationship tables
"""
from sqlalchemy import Column, ForeignKey, Table, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from portal.libs.database.orm import ModelBase

# User role relationship table
portal_user_role = Table(
    'portal_user_role',
    ModelBase.metadata,
    Column('user_id', UUID, ForeignKey('public.portal_user.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID, ForeignKey('public.portal_role.id', ondelete='CASCADE'), primary_key=True),
    schema='public'
)

# Role permission relationship table
portal_role_permission = Table(
    'portal_role_permission',
    ModelBase.metadata,
    Column('permission_id', UUID, ForeignKey('public.portal_permission.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID, ForeignKey('public.portal_role.id', ondelete='CASCADE'), primary_key=True),
    Column('expire_date', DateTime, comment='Expiration time, can be used for temporary authorization'),
    schema='public'
)

# Index for expire_date to speed up queries
Index('ix_portal_role_permission_expire_date', portal_role_permission.c.expire_date)
