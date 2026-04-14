"""
Tests for TicketHandler private registration number helpers.
"""
from uuid import UUID

import pytest

from portal.handlers.ticket import TicketHandler


def test_registration_number_from_ticket_id_readme_sample():
    """
    README sample UUID with year 26 yields 12 digits then XXX-XXXXX-XXXX display.
    """
    ticket_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    assert TicketHandler._registration_digits_from_ticket_id(ticket_id, 26) == "264362908843"
    assert TicketHandler._registration_number_from_ticket_id(ticket_id, 26) == "264-36290-8843"


def test_registration_number_is_deterministic():
    ticket_id = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    first = TicketHandler._registration_number_from_ticket_id(ticket_id, 26)
    second = TicketHandler._registration_number_from_ticket_id(ticket_id, 26)
    assert first == second


def test_year_modulo_100():
    ticket_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    assert TicketHandler._registration_digits_from_ticket_id(ticket_id, 126).startswith("26")


def test_format_registration_number_display_invalid_length():
    with pytest.raises(ValueError):
        TicketHandler._format_registration_number_display("123")
