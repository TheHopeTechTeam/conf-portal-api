"""
Fixture for testing the container module.
"""
import pytest

from portal.container import Container
from portal.libs.database import PostgresConnection, Session


@pytest.fixture
def container() -> Container:
    """
    Fixture for container
    :return:
    """
    container = Container()
    return container


@pytest.fixture
def postgres_pool(container: Container) -> PostgresConnection:
    """
    Fixture for PostgresPool
    :return:
    """
    return container.postgres_connection()


@pytest.fixture
def db_session(container: Container, postgres_pool: PostgresConnection) -> Session:
    """
    Fixture for database session
    :param container:
    :param postgres_pool:
    :return:
    """
    return container.db_session(postgres_pool=postgres_pool)
