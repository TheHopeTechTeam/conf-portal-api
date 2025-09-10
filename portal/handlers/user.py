"""
UserHandler
"""
from typing import Optional

from redis.asyncio import Redis

from portal.config import settings
from portal.libs.database import Session, RedisPool
from portal.schemas.user import UserDetail, UserThirdParty
from portal.models import PortalUser, PortalUserProfile, PortalThirdPartyProvider, PortalUserThirdPartyAuth


class UserHandler:
    """UserHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    async def get_user_detail_by_provider_uid(self, provider_uid: str) -> Optional[UserThirdParty]:
        """
        Get user detail by provider id
        :param provider_uid:
        :return:
        """
        user: UserThirdParty = await (
            self._session.select(
                PortalUser.id,
                PortalUser.phone_number,
                PortalUser.email,
                PortalUser.password_hash,
                PortalUser.verified,
                PortalUser.is_active,
                PortalUser.is_superuser,
                PortalUser.is_admin,
                PortalUser.password_changed_at,
                PortalUser.password_expires_at,
                PortalUser.last_login_at,
                PortalUserProfile.display_name,
                PortalUserProfile.gender,
                PortalUserProfile.is_ministry,
                PortalThirdPartyProvider.id.label("provider_id"),
                PortalThirdPartyProvider.name.label("provider"),
                PortalUserThirdPartyAuth.provider_uid,
                PortalUserThirdPartyAuth.additional_data
            )
            .outerjoin(PortalUserProfile, PortalUser.id == PortalUserProfile.user_id)
            .outerjoin(PortalUserThirdPartyAuth, PortalUser.id == PortalUserThirdPartyAuth.user_id)
            .outerjoin(PortalThirdPartyProvider, PortalUserThirdPartyAuth.provider_id == PortalThirdPartyProvider.id)
            .where(PortalUserThirdPartyAuth.provider_uid == provider_uid)
            .where(PortalUser.is_deleted == False)
            .where(PortalUser.is_active == True)
            .fetchrow(as_model=UserThirdParty)
        )
