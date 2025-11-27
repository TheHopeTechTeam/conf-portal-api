"""
Permission constants
"""
from enum import Enum


class Verb(Enum):
    """Verb enum"""
    READ = "read"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class Resource(Enum):
    """Resource enum"""
    # General resources
    # [comms]
    COMMS_NOTIFICATION = "comms:notification"
    COMMS_NOTIFICATION_HISTORY = "comms:notification_history"

    # [conference]
    CONFERENCE_CONFERENCES = "conference:conferences"
    CONFERENCE_EVENT_SCHEDULE = "conference:event_schedule"

    # [content]
    CONTENT_FILE = "content:file"
    CONTENT_INSTRUCTOR = "content:instructor"
    CONTENT_LOCATION = "content:location"
    CONTENT_TESTIMONY = "content:testimony"

    # [support]
    SUPPORT_FAQ = "support:faq"
    SUPPORT_FEEDBACK = "support:feedback"

    # [workshop]
    WORKSHOP_REGISTRATION = "workshop:registration"
    WORKSHOP_WORKSHOPS = "workshop:workshops"

    # System resources
    SYSTEM_FCM_DEVICE = "system:fcm_device"
    SYSTEM_LOG = "system:log"
    SYSTEM_PERMISSION = "system:permission"
    SYSTEM_RESOURCE = "system:resource"
    SYSTEM_ROLE = "system:role"
    SYSTEM_USER = "system:user"


class Permission:
    """
    Permission
    usage: Permission.{resource}.{verb} can get permission code.
    E.g., Permission.SYSTEM_USER.READ = "system:user:read"
    """

    class PermissionCode:
        """Internal class for generating permission codes"""

        def __init__(self, resource_value: str):
            self._resource_value = resource_value

        @property
        def all(self):
            return f"{self._resource_value}:*"

        @property
        def read(self):
            return f"{self._resource_value}:{Verb.READ.value}"

        @property
        def create(self):
            return f"{self._resource_value}:{Verb.CREATE.value}"

        @property
        def modify(self):
            return f"{self._resource_value}:{Verb.MODIFY.value}"

        @property
        def delete(self):
            return f"{self._resource_value}:{Verb.DELETE.value}"

    # General resources
    # [comms]
    COMMS_NOTIFICATION = PermissionCode(Resource.COMMS_NOTIFICATION.value)
    COMMS_NOTIFICATION_HISTORY = PermissionCode(Resource.COMMS_NOTIFICATION_HISTORY.value)

    # [conference]
    CONFERENCE_CONFERENCES = PermissionCode(Resource.CONFERENCE_CONFERENCES.value)
    CONFERENCE_EVENT_SCHEDULE = PermissionCode(Resource.CONFERENCE_EVENT_SCHEDULE.value)

    # [content]
    CONTENT_FILE = PermissionCode(Resource.CONTENT_FILE.value)
    CONTENT_INSTRUCTOR = PermissionCode(Resource.CONTENT_INSTRUCTOR.value)
    CONTENT_LOCATION = PermissionCode(Resource.CONTENT_LOCATION.value)
    CONTENT_TESTIMONY = PermissionCode(Resource.CONTENT_TESTIMONY.value)

    # [support]
    SUPPORT_FAQ = PermissionCode(Resource.SUPPORT_FAQ.value)
    SUPPORT_FEEDBACK = PermissionCode(Resource.SUPPORT_FEEDBACK.value)

    # [workshop]
    WORKSHOP_REGISTRATION = PermissionCode(Resource.WORKSHOP_REGISTRATION.value)
    WORKSHOP_WORKSHOPS = PermissionCode(Resource.WORKSHOP_WORKSHOPS.value)

    # System resources
    SYSTEM_FCM_DEVICE = PermissionCode(Resource.SYSTEM_FCM_DEVICE.value)
    SYSTEM_LOG = PermissionCode(Resource.SYSTEM_LOG.value)
    SYSTEM_PERMISSION = PermissionCode(Resource.SYSTEM_PERMISSION.value)
    SYSTEM_RESOURCE = PermissionCode(Resource.SYSTEM_RESOURCE.value)
    SYSTEM_ROLE = PermissionCode(Resource.SYSTEM_ROLE.value)
    SYSTEM_USER = PermissionCode(Resource.SYSTEM_USER.value)

