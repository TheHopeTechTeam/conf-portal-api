"""
One-time cleanup script for workshop registrations.

Delete scope:
- User has ONLINE_PASS_SINGLE tickets only (INTERPRETATION_RECEIVER is allowed as addon).
- If user has any other ticket code, user is excluded.

Action:
- Soft delete all non-deleted PortalWorkshopRegistration rows for matched users.
"""
import argparse
import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin
from typing import Iterable
from uuid import UUID

import sqlalchemy as sa
from httpx import HTTPStatusError

from portal.config import settings
from portal.container import Container
from portal.libs.database import Session
from portal.libs.http_client import http_client
from portal.libs.logger import logger
from portal.models import PortalUser, PortalWorkshopRegistration
from portal.schemas.thehope_ticket import TheHopeTicket

ONLINE_PASS_CODE = "ONLINE_PASS_SINGLE"
INTERPRETATION_RECEIVER_CODE = "INTERPRETATION_RECEIVER"
ALLOWED_CODES = {
    ONLINE_PASS_CODE,
    INTERPRETATION_RECEIVER_CODE,
}
DEFAULT_DELETE_REASON = "cleanup_online_pass_workshop_registrations"
DEFAULT_EMAIL_QUERY_BATCH_SIZE = 100


@dataclass
class CleanupStats:
    scanned_user_count: int = 0
    matched_user_count: int = 0
    skipped_user_count: int = 0
    failed_user_count: int = 0
    matched_registration_count: int = 0
    updated_registration_count: int = 0
    errors: list[str] = field(default_factory=list)


def _extract_ticket_codes(tickets: Iterable[TheHopeTicket]) -> set[str]:
    ticket_codes: set[str] = set()
    for ticket in tickets:
        meta = ticket.ticket_type.meta or {}
        conf_code = meta.get("conf_code")
        if isinstance(conf_code, str) and conf_code.strip():
            ticket_codes.add(conf_code.strip())
    return ticket_codes


def _is_target_user_ticket_set(ticket_codes: set[str]) -> bool:
    if ONLINE_PASS_CODE not in ticket_codes:
        return False
    disallowed_codes = ticket_codes - ALLOWED_CODES
    return not disallowed_codes


async def _fetch_tickets_by_email(user_emails: str) -> list[TheHopeTicket]:
    base_url = f"{settings.THEHOPE_TICKET_SYSTEM_URL}/api/"
    url = urljoin(base_url, "v1/tickets")
    headers = {
        "x-external-service-token": settings.THEHOPE_TICKET_SYSTEM_API_KEY,
    }
    query_params = {
        "trash": False,
        "where[user.email][in]": user_emails,
        "limit": DEFAULT_EMAIL_QUERY_BATCH_SIZE,
    }
    try:
        response = await (
            http_client.create(url)
            .add_headers(headers)
            .add_query(query_params)
            .verbose(False)
            .aget()
        )
        response.raise_for_status()
    except HTTPStatusError:
        raise
    payload = response.json()
    raw_tickets = payload.get("docs", []) if isinstance(payload, dict) else []
    if not isinstance(raw_tickets, list):
        return []
    return [TheHopeTicket.model_validate(item) for item in raw_tickets]


def _chunk_list(items: list[str | UUID], chunk_size: int) -> list:
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]


async def _fetch_tickets_grouped_by_email(user_emails: list[str]) -> dict[str, list[TheHopeTicket]]:
    grouped_tickets: dict[str, list[TheHopeTicket]] = {email: [] for email in user_emails}
    if not user_emails:
        return grouped_tickets

    for email_batch in _chunk_list(user_emails, DEFAULT_EMAIL_QUERY_BATCH_SIZE):
        batch_query_value = ",".join(email_batch)
        batch_tickets = await _fetch_tickets_by_email(user_emails=batch_query_value)
        for ticket in batch_tickets:
            ticket_user_email = ticket.user.email
            if not ticket_user_email:
                continue
            if ticket_user_email not in grouped_tickets:
                continue
            grouped_tickets[ticket_user_email].append(ticket)
    return grouped_tickets


async def _load_candidate_users(session: Session) -> list[dict]:
    rows = await (
        session.select(
            PortalUser.id.label("user_id"),
            PortalUser.email.label("email"),
            sa.func.count(PortalWorkshopRegistration.id).label("registration_count"),
        )
        .join(PortalWorkshopRegistration, PortalWorkshopRegistration.user_id == PortalUser.id)
        .where(PortalWorkshopRegistration.is_deleted == sa.false())
        .group_by(PortalUser.id, PortalUser.email)
        .fetch()
    )
    return [
        {
            "user_id": row["user_id"],
            "email": row["email"],
            "registration_count": row["registration_count"] or 0,
        }
        for row in rows
    ]


async def _soft_delete_user_registrations(
    session: Session,
    user_ids: list[UUID],
    delete_reason: str,
) -> None:
    if not user_ids:
        return
    await (
        session.update(PortalWorkshopRegistration)
        .where(PortalWorkshopRegistration.user_id.in_(user_ids))
        .where(PortalWorkshopRegistration.is_deleted == sa.false())
        .values(
            is_deleted=True,
            delete_reason=delete_reason,
        )
        .execute()
    )


async def run_cleanup(
    *,
    dry_run: bool,
    batch_size: int,
    delete_reason: str,
) -> CleanupStats:
    container = Container()
    postgres_connection = container.postgres_connection()
    session = container.db_session(postgres_connection=postgres_connection)
    stats = CleanupStats()
    matched_user_ids: list[UUID] = []

    try:
        candidate_users = await _load_candidate_users(session=session)
        stats.scanned_user_count = len(candidate_users)
        logger.info("Loaded %s candidate users with workshop registrations.", stats.scanned_user_count)
        candidate_emails = [item["email"] for item in candidate_users]
        tickets_by_email = await _fetch_tickets_grouped_by_email(user_emails=candidate_emails)

        for user in candidate_users:
            user_id: UUID = user["user_id"]
            email: str = user["email"]
            registration_count: int = user["registration_count"]
            try:
                tickets = tickets_by_email.get(email, [])
                ticket_codes = _extract_ticket_codes(tickets=tickets)
                if not _is_target_user_ticket_set(ticket_codes=ticket_codes):
                    stats.skipped_user_count += 1
                    continue

                if registration_count <= 0:
                    stats.skipped_user_count += 1
                    continue

                stats.matched_user_count += 1
                stats.matched_registration_count += registration_count
                matched_user_ids.append(user_id)
            except Exception as e:
                stats.failed_user_count += 1
                error_message = f"user_id={user_id}, email={email}, error={e}"
                stats.errors.append(error_message)
                logger.exception("Failed processing user for workshop cleanup: %s", error_message)

        if not dry_run and matched_user_ids:
            user_id_chunks = _chunk_list(matched_user_ids, batch_size)
            for user_id_chunk in user_id_chunks:
                await _soft_delete_user_registrations(
                    session=session,
                    user_ids=user_id_chunk,
                    delete_reason=delete_reason,
                )
                await session.commit()
            stats.updated_registration_count = stats.matched_registration_count
    finally:
        await session.close()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cleanup workshop registrations for users with only ONLINE_PASS_SINGLE tickets."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview affected users and registration counts without database updates.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Commit every N matched users in non-dry-run mode.",
    )
    parser.add_argument(
        "--delete-reason",
        type=str,
        default=DEFAULT_DELETE_REASON,
        help="Delete reason written to portal_workshop_registration.delete_reason.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be a positive integer.")

    stats = await run_cleanup(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        delete_reason=args.delete_reason,
    )

    logger.info("===== Online Pass Workshop Cleanup Summary =====")
    logger.info("dry_run: %s", args.dry_run)
    logger.info("scanned_user_count: %s", stats.scanned_user_count)
    logger.info("matched_user_count: %s", stats.matched_user_count)
    logger.info("skipped_user_count: %s", stats.skipped_user_count)
    logger.info("failed_user_count: %s", stats.failed_user_count)
    logger.info("matched_registration_count: %s", stats.matched_registration_count)
    logger.info("updated_registration_count: %s", stats.updated_registration_count)
    if stats.errors:
        logger.error("errors:")
        for item in stats.errors:
            logger.error("- %s", item)


if __name__ == "__main__":
    asyncio.run(main())
