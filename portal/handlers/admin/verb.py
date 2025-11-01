"""
AdminVerbHandler
"""
from redis.asyncio import Redis

from portal.config import settings
from portal.libs.consts.cache_keys import CacheKeys, CacheExpiry
from portal.libs.database import Session, RedisPool
from portal.models import PortalVerb
from portal.serializers.v1.admin.verb import VerbList, VerbItem


class AdminVerbHandler:
    """AdminVerbHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)


    async def get_verb_list(self) -> VerbList:
        """

        :return:
        """
        cache_key = CacheKeys(resource="verb").add_attribute("list").build()
        cached = await self._redis.get(cache_key)
        if cached:
            return VerbList.model_validate_json(cached)
        verbs: list[VerbItem] = await (
            self._session.select(
                PortalVerb.id,
                PortalVerb.action,
                PortalVerb.display_name,
                PortalVerb.description,
            )
            .where(PortalVerb.is_active == True)
            .where(PortalVerb.is_deleted == False)
            .order_by(PortalVerb.created_at)
            .fetch(as_model=VerbItem)
        )
        if not verbs:
            return VerbList(items=[])
        result = VerbList(items=verbs)
        await self._redis.set(
            cache_key,
            result.model_dump_json(),
            ex=CacheExpiry.MONTH,
        )
        return result
