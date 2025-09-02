"""
Shared request context fixtures for tests.
"""
import pytest

from portal.libs.contexts.request_context import RequestContext, set_request_context, request_context_var


@pytest.fixture
def request_context():
    token = set_request_context(RequestContext(ip="127.0.0.1", client_ip="127.0.0.1", user_agent="pytest/ua"))
    try:
        yield
    finally:
        request_context_var.reset(token)



