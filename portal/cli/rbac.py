"""
RBAC initialization CLI commands.
"""
import asyncio

import click

from portal.container import Container
from portal.libs.logger import logger
from portal.models.rbac import (
    PortalRole,
    PortalResource,
    PortalVerb,
    PortalPermission,
    PortalRolePermission,
)


async def init_rbac():
    """
    Seed verbs, resources, permissions, roles, and role-permission mappings.
    Idempotent: uses ON CONFLICT DO NOTHING on unique keys.
    """
    container = Container()
    session = container.db_session()

    try:
        # 1) Seed verbs
        verbs = [
            {"action": "create", "display_name": "新增"},
            {"action": "read", "display_name": "查看"},
            {"action": "modify", "display_name": "編輯"},
            {"action": "delete", "display_name": "刪除"}
        ]
        for v in verbs:
            await (
                session
                .insert(PortalVerb)
                .values(action=v["action"], display_name=v.get("display_name"))
                .on_conflict_do_nothing(index_elements=["action"])
                .execute()
            )

        # 2) Seed resources (subset aligned with docs/rbac-design.md)
        resources = [
            {"code": "system:user", "name": "使用者管理", "key": "SYSTEM_USER", "icon": "users", "path": "/system/users", "description": "管理系統使用者"},
            {"code": "system:role", "name": "角色管理", "key": "SYSTEM_ROLE", "icon": "shield", "path": "/system/roles", "description": "管理系統角色"},
            {"code": "system:permission", "name": "權限管理", "key": "SYSTEM_PERMISSION", "icon": "key", "path": "/system/permissions", "description": "管理系統權限"},
            {"code": "system:resource", "name": "資源管理", "key": "SYSTEM_RESOURCE", "icon": "folder", "path": "/system/resources", "description": "管理系統資源"},
            {"code": "system:log", "name": "系統日誌", "key": "SYSTEM_LOG", "icon": "file-text", "path": "/system/logs", "description": "管理系統日誌"},
            {"code": "system:fcm_device", "name": "FCM裝置管理", "key": "SYSTEM_FCM_DEVICE", "icon": "smartphone", "path": "/system/devices", "description": "管理系統FCM裝置"},
            {"code": "conference:basic", "name": "會議管理", "key": "CONFERENCE_BASIC", "icon": "calendar", "path": "/conferences", "description": "管理會議"},
            {"code": "conference:instructor", "name": "會議講師", "key": "CONFERENCE_INSTRUCTOR", "icon": "user-check", "path": "/conferences/instructors", "description": "管理會議講師"},
            {"code": "conference:event_schedule", "name": "活動時程", "key": "CONFERENCE_EVENT_SCHEDULE", "icon": "clock", "path": "/conferences/events", "description": "管理會議活動時程"},
            {"code": "workshop:basic", "name": "工作坊", "key": "WORKSHOP_BASIC", "icon": "briefcase", "path": "/workshops", "description": "管理工作坊"},
            {"code": "workshop:registration", "name": "工作坊報名", "key": "WORKSHOP_REGISTRATION", "icon": "clipboard", "path": "/workshops/registrations", "description": "管理工作坊報名"},
            {"code": "comms:notification", "name": "通知管理", "key": "COMMS_NOTIFICATION", "icon": "bell", "path": "/comms/notifications", "description": "管理通知"},
            {"code": "comms:notification_history", "name": "通知歷史", "key": "COMMS_NOTIFICATION_HISTORY", "icon": "archive", "path": "/comms/notification-history", "description": "管理通知歷史"},
            {"code": "content:faq", "name": "FAQ", "key": "CONTENT_FAQ", "icon": "help-circle", "path": "/content/faq", "description": "管理FAQ"},
            {"code": "content:testimony", "name": "見證", "key": "CONTENT_TESTIMONY", "icon": "message-circle", "path": "/content/testimonies", "description": "管理見證"},
            {"code": "content:instructor", "name": "講師", "key": "CONTENT_INSTRUCTOR", "icon": "user", "path": "/content/instructors", "description": "管理講師"},
            {"code": "content:location", "name": "地點", "key": "CONTENT_LOCATION", "icon": "map-pin", "path": "/content/locations", "description": "管理地點"},
            {"code": "content:file", "name": "檔案", "key": "CONTENT_FILE", "icon": "file", "path": "/content/files", "description": "管理檔案"},
            {"code": "support:feedback", "name": "意見回饋", "key": "SUPPORT_FEEDBACK", "icon": "message-square", "path": "/support/feedback", "description": "管理意見回饋"}
        ]
        for r in resources:
            await (
                session
                .insert(PortalResource)
                .values(
                    code=r["code"],
                    key=r.get("key", r["code"]),
                    name=r.get("name"),
                    icon=r.get("icon"),
                    path=r.get("path"),
                    is_visible=True,
                    description=r.get("description")
                )
                .on_conflict_do_update(
                    index_elements=["code"],
                    set_=dict(
                        key=r.get("key", r["code"]),
                        name=r.get("name"),
                        icon=r.get("icon"),
                        path=r.get("path"),
                        is_visible=True,
                        description=r.get("description")
                    )
                )
                .execute()
            )

        # 3) Fetch current verbs/resources for id mapping
        verb_rows = await session.select(PortalVerb).fetch()
        resource_rows = await session.select(PortalResource).fetch()
        action_to_verb_id = {row["action"]: row["id"] for row in verb_rows}
        resource_code_to = {row["code"]: row for row in resource_rows}

        # 4) Seed permissions: resource x verb
        for res_code, res in resource_code_to.items():
            for action, verb_id in action_to_verb_id.items():
                code = f"{res_code}:{action}"
                display_name = f"{res.get('name') or res_code} {action.capitalize()}"
                description = f"可在{res.get('description')}上操作 {action.capitalize()}"
                await (
                    session
                    .insert(PortalPermission)
                    .values(
                        code=code,
                        resource_id=res["id"],
                        verb_id=verb_id,
                        display_name=display_name,
                        is_active=True,
                        description=description
                    )
                    .on_conflict_do_update(
                        index_elements=["code"],
                        set_=dict(
                            display_name=display_name,
                            is_active=True,
                            description=description
                        )
                    )
                    .execute()
                )

        # 5) Roles: keep only one role `admin`
        # Delete any roles other than 'admin' (cascades will clean associations)
        await (
            session
            .delete(PortalRole)
            .where(PortalRole.code != 'admin')
            .execute()
        )
        # Ensure `admin` role exists
        await (
            session
            .insert(PortalRole)
            .values(code='admin', name='系統管理員', is_active=True)
            .on_conflict_do_nothing(index_elements=["code"])
            .execute()
        )

        # Permissions lookup
        perm_rows = await session.select(PortalPermission).fetch()
        code_to_perm = {row["code"]: row for row in perm_rows}

        # 6) Grant permissions to `admin`: all except resource:* and verb:*
        excluded_prefixes = ("system:resource:", "system:verb:", "system:fcm_device:", "comms:notification")

        # Fetch admin role id
        admin_row = await (
            session
            .select(PortalRole)
            .where(PortalRole.code == 'admin')
            .fetchrow()
        )
        inserted_count = 0
        if admin_row:
            for p_code, perm_row in code_to_perm.items():
                if p_code.startswith(excluded_prefixes):
                    continue
                await (
                    session
                    .insert(PortalRolePermission)
                    .values(role_id=admin_row["id"], permission_id=perm_row["id"])
                    .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
                    .execute()
                )
                inserted_count += 1

        await session.commit()
        click.echo(click.style("RBAC initialized successfully.", fg="bright_green"))
        logger.info(f"RBAC init completed. role-permissions inserted/ensured: {inserted_count}")
    except Exception as e:
        await session.rollback()
        click.echo(click.style(f"RBAC init failed: {e}", fg="red"))
        logger.exception(e)
        raise
    finally:
        await session.close()


def init_rbac_process():
    """Synchronous entry to run RBAC initialization."""
    click.echo(click.style("Initializing RBAC (verbs, resources, permissions, roles)...", fg="cyan"))
    asyncio.run(init_rbac())
    click.echo(click.style("Done.", fg="green"))
