"""
Superuser related CLI commands.
"""
import asyncio
from uuid import uuid4

import click
import phonenumbers
from phonenumbers import PhoneNumberFormat

from portal.container import Container
from portal.libs.shared import validator
from portal.models.rbac import PortalUser, PortalUserProfile
from portal.providers.password_provider import PasswordProvider


async def create_superuser(
    email: str,
    phone_number: str,
    password: str,
    display_name: str | None = None,
):
    """
    Create a superuser.
    """
    container = Container()
    session = container.db_session()
    password_provider = PasswordProvider()

    try:
        existing_user = await (
            session
            .select(PortalUser)
            .where((PortalUser.email == email) | (PortalUser.phone_number == phone_number))
            .fetchrow()
        )
        if existing_user:
            click.echo(f"User already exists for email '{email}' or phone '{phone_number}'.")
            return existing_user

        password_hash = password_provider.hash_password(password)

        user_id = uuid4()
        await (
            session
            .insert(PortalUser)
            .values(
                id=user_id,
                phone_number=phone_number,
                email=email,
                password_hash=password_hash,
                verified=True,
                is_active=True,
                is_admin=False,
                is_superuser=True,
            )
            .execute()
        )

        await (
            session
            .insert(PortalUserProfile)
            .values(
                id=uuid4(),
                user_id=user_id,
                display_name=display_name or email,
            )
            .execute()
        )

        await session.commit()
        click.echo(f"Superuser created: {email} ({phone_number})")
        return await session.select(PortalUser).where(PortalUser.id == user_id).fetchrow()
    except Exception as e:
        click.echo(f"Error creating superuser: {e}")
        await session.rollback()
        return None
    finally:
        await session.close()


def create_superuser_process():
    """Create a superuser via interactive prompts."""
    click.echo(f"\nThis process will guide you through the process of creating a {click.style('superuser', fg='blue')} account in the portal.")
    click.echo("Please enter the following information to create a superuser account.\n")
    while True:
        email = click.prompt(
            click.style("Enter superuser email (e.g., admin@example.com)", fg="green"),
            type=str
        )
        if not validator.is_email(email):
            click.echo(
                click.style("Invalid email format. Please enter a valid email address.", fg="red")
            )
            continue
        break
    # Validate and normalize phone number to E.164 using phonenumbers
    while True:
        raw_phone = click.prompt(
            click.style("Enter superuser phone number (International format, e.g., +886912345678)", fg="green"),
            type=str
        )
        try:
            parsed = phonenumbers.parse(raw_phone, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            phone_number = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
            break
        except Exception:
            click.echo(
                click.style("Invalid phone number format. Please enter a valid international format number like +886912345678.", fg="red")
            )
    password = click.prompt(
        click.style("Enter superuser password", fg="green"),
        hide_input=True,
        confirmation_prompt=click.style("Confirm password", fg="yellow"),
        type=str
    )
    display_name = click.prompt(
        click.style("Enter display name (optional)", fg="green"),
        default="",
        show_default=False,
        type=str
    )
    display_name = display_name or None

    asyncio.run(create_superuser(email=email, phone_number=phone_number, password=password, display_name=display_name))
    click.echo(
        click.style(f"\nSuperuser created successfully: {email} ({phone_number})", fg="bright_green")
    )
