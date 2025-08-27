"""
Fixtures for file handler tests.
"""
import pytest

from portal.container import Container
from portal.handlers import FileHandler


@pytest.fixture
def file_handler() -> FileHandler:
    """Get the file handler."""
    container = Container()
    return container.file_handler()
