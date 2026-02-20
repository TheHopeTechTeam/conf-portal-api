"""
Enums for the application
"""
from enum import Enum, IntEnum


class AccessTokenAudType(Enum):
    """
    Access token audience type
    """
    ADMIN = "admin"
    APP = "app"


class AuthProvider(Enum):
    """
    Third-party authentication provider
    """
    FIREBASE = "firebase"


class Gender(IntEnum):
    """
    Gender
    """
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2
    OTHER = 3


class ResourceType(IntEnum):
    """
    Resource type
    """
    SYSTEM = 0
    GENERAL = 1


class FileStatus(IntEnum):
    """
    File status
    """
    UPLOADING = 0
    UPLOADED = 1
    PROCESSING = 2
    PROCESSED = 3
    FAILED = 4
    DELETED = 5


class FileUploadSource(IntEnum):
    """
    File upload source
    """
    ADMIN = 0
    APP = 1


class FeedbackStatus(IntEnum):
    """
    Feedback status
    """
    PENDING = 0
    REVIEW = 1
    DISCUSSION = 2
    ACCEPTED = 3
    DONE = 4
    REJECTED = 5
    ARCHIVED = 6


class NotificationMethod(IntEnum):
    """
    Notification method
    """
    PUSH = 0
    EMAIL = 1


class NotificationType(IntEnum):
    """
    Notification type
    """
    SYSTEM = 0
    MULTIPLE = 1
    INDIVIDUAL = 2


class NotificationStatus(IntEnum):
    """
    Notification status
    """
    PENDING = 0
    SENT = 1
    FAILED = 2
    DRY_RUN = 3


class NotificationHistoryStatus(IntEnum):
    """
    Notification history status
    """
    PENDING = 0
    SUCCESS = 1
    FAILED = 2
    DRY_RUN = 3


class Identity(Enum):
    """Identity"""
    SENIOR_PASTOR = "senior_pastor"
    PASTOR = "pastor"
    EVANGELIST = "evangelist"
    THEOLOGY_STUDENT = "theology_student"
    MINISTRY_LEADER = "ministry_leader"
    CONGREGANT = "congregant"


class OperationType(Enum):
    """Operation Type"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    RECYCLE = "recycle"
    LOGIN = "login"
    LOGOUT = "logout"
    OTHER = "other"
