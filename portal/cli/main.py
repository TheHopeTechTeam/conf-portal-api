"""
Main Click CLI entry aggregating all subcommands.
"""
import click

from .superuser import create_superuser_process
from .rbac import init_rbac_process


@click.group()
def cli():
    """Portal CLI"""
    pass


# Register subcommands
@cli.command(name="create-superuser")
def create_superuser_cmd():
    """Create a superuser via interactive prompts."""
    create_superuser_process()


@cli.command(name="init-rbac")
def init_rbac_cmd():
    """Initialize RBAC data (verbs/resources/permissions/roles)."""
    init_rbac_process()


def main() -> int:
    cli()
    return 0
