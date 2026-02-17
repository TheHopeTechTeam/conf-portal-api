"""
Constants for ticket type sync (TTL and Redis key)
"""

# Redis key storing last sync timestamp (value: float as string)
REDIS_KEY_TICKET_TYPE_SYNC_AT = "portal:ticket_type_sync_at"

# Consider sync stale after this many seconds; trigger sync on list API when stale
TICKET_TYPE_SYNC_TTL_SECONDS = 3600
