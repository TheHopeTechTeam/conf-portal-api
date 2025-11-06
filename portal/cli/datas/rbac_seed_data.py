"""
Seed data for RBAC CLI: verbs, parent resources, child resources, and exclusions.
"""
from uuid import UUID

from portal.libs.consts.enums import ResourceType

# Parent resource IDs (constants)
SYSTEM_PARENT_ID = UUID("b46586f5-7e43-4eed-9f44-fecff64c9b1d")
CONFERENCE_PARENT_ID = UUID("902bc7d2-8c42-40e6-9a8e-8bf12fc0efc5")
WORKSHOP_PARENT_ID = UUID("d92c0e66-0ac4-475c-981e-8989c7e5f472")
COMMS_PARENT_ID = UUID("342a72a7-544a-4967-8841-c11c9cf7ccd9")
CONTENT_PARENT_ID = UUID("bbc09c99-28b9-4d37-a1c7-c44a427cbfbf")
SUPPORT_PARENT_ID = UUID("0450da45-9482-4321-81a3-1fddcf6264e5")

# Verbs
seed_verbs = [
    {"action": "create", "display_name": "新增"},
    {"action": "read", "display_name": "查看"},
    {"action": "modify", "display_name": "編輯"},
    {"action": "delete", "display_name": "刪除"},
]

# Parent resources (grouping only)
parent_resources = [
    {
        "id": SYSTEM_PARENT_ID,
        "code": "system",
        "name": "系統管理",
        "key": "SYSTEM",
        "icon": "settings",
        "path": "/system",
        "description": "系統相關管理",
        "type": ResourceType.SYSTEM.value
    },
    {
        "id": COMMS_PARENT_ID,
        "code": "comms",
        "name": "通知管理",
        "key": "COMMS",
        "icon": "bell",
        "path": "/comms",
        "description": "通知與溝通",
        "type": ResourceType.SYSTEM.value
    },
    {
        "id": CONFERENCE_PARENT_ID,
        "code": "conference",
        "name": "會議管理",
        "key": "CONFERENCE",
        "icon": "calendar",
        "path": "/conference",
        "description": "會議相關管理",
        "type": ResourceType.GENERAL.value
    },
    {
        "id": WORKSHOP_PARENT_ID,
        "code": "workshop",
        "name": "工作坊管理",
        "key": "WORKSHOP",
        "icon": "briefcase",
        "path": "/workshop",
        "description": "工作坊相關管理",
        "type": ResourceType.GENERAL.value
    },
    {
        "id": CONTENT_PARENT_ID,
        "code": "content",
        "name": "內容管理",
        "key": "CONTENT",
        "icon": "folder",
        "path": "/content",
        "description": "內容相關管理",
        "type": ResourceType.GENERAL.value
    },
    {
        "id": SUPPORT_PARENT_ID,
        "code": "support",
        "name": "客服支援管理",
        "key": "SUPPORT",
        "icon": "life-buoy",
        "path": "/support",
        "description": "支援與回饋",
        "type": ResourceType.GENERAL.value
    },
]

# Leaf resources (permissions will be created for these)
resources = [
    {
        "code": "system:user",
        "name": "使用者管理",
        "key": "SYSTEM_USER",
        "icon": "users",
        "path": "/system/users",
        "description": "管理系統使用者",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "system:role",
        "name": "角色管理",
        "key": "SYSTEM_ROLE",
        "icon": "shield",
        "path": "/system/roles",
        "description": "管理系統角色",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "system:permission",
        "name": "權限管理",
        "key": "SYSTEM_PERMISSION",
        "icon": "key",
        "path": "/system/permissions",
        "description": "管理系統權限",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "system:resource",
        "name": "資源管理",
        "key": "SYSTEM_RESOURCE",
        "icon": "folder",
        "path": "/system/resources",
        "description": "管理系統資源",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "system:log",
        "name": "系統日誌",
        "key": "SYSTEM_LOG",
        "icon": "file-text",
        "path": "/system/logs",
        "description": "管理系統日誌",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "system:fcm_device",
        "name": "FCM裝置管理",
        "key": "SYSTEM_FCM_DEVICE",
        "icon": "smartphone",
        "path": "/system/devices",
        "description": "管理系統FCM裝置",
        "pid": SYSTEM_PARENT_ID
    },
    {
        "code": "conference:conferences",
        "name": "會議",
        "key": "CONFERENCE_BASIC",
        "icon": "calendar",
        "path": "/conference/conferences",
        "description": "管理會議",
        "pid": CONFERENCE_PARENT_ID
    },
    {
        "code": "conference:instructor",
        "name": "會議講師",
        "key": "CONFERENCE_INSTRUCTOR",
        "icon": "user-check",
        "path": "/conference/instructors",
        "description": "管理會議講師",
        "pid": CONFERENCE_PARENT_ID
    },
    {
        "code": "conference:event_schedule",
        "name": "活動時程",
        "key": "CONFERENCE_EVENT_SCHEDULE",
        "icon": "clock",
        "path": "/conference/events",
        "description": "管理會議活動時程",
        "pid": CONFERENCE_PARENT_ID
    },
    {
        "code": "workshop:workshops",
        "name": "工作坊",
        "key": "WORKSHOP_BASIC",
        "icon": "briefcase",
        "path": "/workshop/workshops",
        "description": "管理工作坊",
        "pid": WORKSHOP_PARENT_ID
    },
    {
        "code": "workshop:registration",
        "name": "工作坊報名",
        "key": "WORKSHOP_REGISTRATION",
        "icon": "clipboard",
        "path": "/workshop/registrations",
        "description": "管理工作坊報名",
        "pid": WORKSHOP_PARENT_ID
    },
    {
        "code": "comms:notification",
        "name": "通知管理",
        "key": "COMMS_NOTIFICATION",
        "icon": "bell",
        "path": "/comms/notifications",
        "description": "管理通知",
        "pid": COMMS_PARENT_ID
    },
    {
        "code": "comms:notification_history",
        "name": "通知歷史",
        "key": "COMMS_NOTIFICATION_HISTORY",
        "icon": "archive",
        "path": "/comms/notification-history",
        "description": "管理通知歷史",
        "pid": COMMS_PARENT_ID
    },
    {
        "code": "content:faq",
        "name": "FAQ",
        "key": "CONTENT_FAQ",
        "icon": "help-circle",
        "path": "/content/faq",
        "description": "管理FAQ",
        "pid": CONTENT_PARENT_ID
    },
    {
        "code": "content:testimony",
        "name": "見證",
        "key": "CONTENT_TESTIMONY",
        "icon": "message-circle",
        "path": "/content/testimonies",
        "description": "管理見證",
        "pid": CONTENT_PARENT_ID
    },
    {
        "code": "content:instructor",
        "name": "講師",
        "key": "CONTENT_INSTRUCTOR",
        "icon": "user",
        "path": "/content/instructors",
        "description": "管理講師",
        "pid": CONTENT_PARENT_ID
    },
    {
        "code": "content:location",
        "name": "地點",
        "key": "CONTENT_LOCATION",
        "icon": "map-pin",
        "path": "/content/locations",
        "description": "管理地點",
        "pid": CONTENT_PARENT_ID
    },
    {
        "code": "content:file",
        "name": "檔案",
        "key": "CONTENT_FILE",
        "icon": "file",
        "path": "/content/files",
        "description": "管理檔案",
        "pid": CONTENT_PARENT_ID
    },
    {
        "code": "support:feedback",
        "name": "意見回饋",
        "key": "SUPPORT_FEEDBACK",
        "icon": "message-square",
        "path": "/support/feedback",
        "description": "管理意見回饋",
        "pid": SUPPORT_PARENT_ID
    },
]
