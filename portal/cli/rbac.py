"""
RBAC initialization CLI commands.
"""
import asyncio

import click

from portal.container import Container
from portal.libs.consts.enums import ResourceType
from portal.libs.logger import logger
from portal.models import (
    PortalRole,
    PortalResource,
    PortalVerb,
    PortalPermission,
    PortalRolePermission,
)
from .datas.rbac_seed_data import (
    seed_verbs,
    parent_resources,
    resources,
)


async def init_rbac():
    """
    Seed verbs, resources, permissions, roles, and role-permission mappings.
    Idempotent: uses ON CONFLICT DO NOTHING on unique keys.
    """
    container = Container()
    session = container.db_session()

    try:
        # Load seed data from portal.cli.datas.rbac_seed_data

        # 1) Seed verbs
        verbs = seed_verbs
        for v in verbs:
            await (
                session
                .insert(PortalVerb)
                .values(action=v["action"], display_name=v.get("display_name"))
                .on_conflict_do_nothing(index_elements=["action"])
                .execute()
            )

        # 2) Seed parent resources for grouping
        # parent_resources imported
        for pr in parent_resources:
            await (
                session
                .insert(PortalResource)
                .values(
                    id=pr.get("id"),
                    code=pr["code"],
                    key=pr.get("key", pr["code"]).upper(),
                    name=pr.get("name"),
                    icon=pr.get("icon"),
                    path=pr.get("path"),
                    type=pr.get("type", ResourceType.GENERAL.value),
                    is_visible=True,
                    description=pr.get("description")
                )
                .on_conflict_do_update(
                    index_elements=["code"],
                    set_=dict(
                        key=pr.get("key", pr["code"]).upper(),
                        name=pr.get("name"),
                        icon=pr.get("icon"),
                        path=pr.get("path"),
                        pid=pr.get("pid"),
                        type=pr.get("type", ResourceType.GENERAL.value),
                        is_visible=True,
                        description=pr.get("description")
                    )
                )
                .execute()
            )

        # 3) Seed leaf resources (subset aligned with docs/rbac-design.md)
        # resources imported
        for r in resources:
            parent_prefix = r["code"].split(":", 1)[0]
            resource_type_value = ResourceType.SYSTEM.value if parent_prefix in ("system", "comms") else ResourceType.GENERAL.value
            await (
                session
                .insert(PortalResource)
                .values(
                    code=r["code"],
                    key=r.get("key", r["code"]),
                    name=r.get("name"),
                    icon=r.get("icon"),
                    path=r.get("path"),
                    pid=r.get("pid"),
                    type=resource_type_value,
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
                        pid=r.get("pid"),
                        type=resource_type_value,
                        is_visible=True,
                        description=r.get("description")
                    )
                )
                .execute()
            )

        # 4) Fetch current verbs/resources for id mapping
        verb_rows = await session.select(PortalVerb).fetch()
        resource_rows = await session.select(PortalResource).fetch()
        action_to_verb_id = {row["action"]: row["id"] for row in verb_rows}
        resource_code_to = {row["code"]: row for row in resource_rows}

        # 5) Seed permissions: resource x verb (skip parent-only resources)
        for res_code, res in resource_code_to.items():
            if ":" not in res_code:
                continue
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

        # 6) Roles: keep only one role `admin`
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

        # 7) Grant permissions to `admin`: all except resource:* and verb:*
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
