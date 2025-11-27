"""
Tests for portal.providers.password_provider.PasswordProvider
"""
import base64

import pytest

from portal.providers.password_provider import PasswordProvider


def test_hash_password_length(password_provider: PasswordProvider) -> None:
    """
    Ensure the hashed password is a fixed length string.
    """
    # No external salt anymore; ensure hashing returns 512-char token
    hash_password = password_provider.hash_password(password="dummy")
    assert isinstance(hash_password, str)
    assert hash_password.startswith("pbkdf2_sha256$")
    assert len(hash_password) == 512
    hash_password = password_provider.hash_password(password="another@gbab146")
    assert isinstance(hash_password, str)
    assert hash_password.startswith("pbkdf2_sha256$")
    assert len(hash_password) == 512


def test_hash_password_returns_fixed_length_token(password_provider: PasswordProvider) -> None:
    """
    Hashing without salt should return a base64 string and generated salt.
    """
    password = "S3cret!Passw0rd"
    password_hash = password_provider.hash_password(password=password)

    assert isinstance(password_hash, str)
    assert password_hash.startswith("pbkdf2_sha256$")
    assert len(password_hash) == 512


def test_hash_password_is_random_due_to_embedded_salt(password_provider: PasswordProvider) -> None:
    """
    With PBKDF2HMAC, same password and same salt yield the same derived key.
    """
    password = "Another$ecret123"
    hash1 = password_provider.hash_password(password=password)
    hash2 = password_provider.hash_password(password=password)

    assert hash1 != hash2
    assert password_provider.verify_password(password=password, password_hash=hash1)
    assert password_provider.verify_password(password=password, password_hash=hash2)


def test_verify_password_success(password_provider: PasswordProvider) -> None:
    password = "P@ssw0rd!"
    password_hash = password_provider.hash_password(password=password)
    assert password_provider.verify_password(password=password, password_hash=password_hash)


def test_verify_password_failure_wrong_password(password_provider: PasswordProvider) -> None:
    password = "CorrectHorseBatteryStaple"
    wrong_password = "Tr0ub4dor&3"
    password_hash = password_provider.hash_password(password=password)
    assert not password_provider.verify_password(password=wrong_password, password_hash=password_hash)


def test_verify_password_failure_invalid_hash(password_provider: PasswordProvider) -> None:
    password = "hello-world"
    invalid_hash = "invalid_format_hash"
    assert not password_provider.verify_password(password=password, password_hash=invalid_hash)


def test_verify_password_failure_version_mismatch(password_provider: PasswordProvider) -> None:
    """
    Tampering with the embedded version byte should invalidate the hash.
    """
    password = "HelloWorld!123"
    password_hash = password_provider.hash_password(password=password)

    token = password_hash.split("$", 1)[1]
    padded_token = token + ("=" * (-len(token) % 4))
    payload = bytearray(base64.urlsafe_b64decode(padded_token.encode("utf-8")))
    payload[0] = (payload[0] + 1) % 256
    tampered_token = base64.urlsafe_b64encode(bytes(payload)).decode("utf-8").rstrip("=")
    tampered_hash = f"pbkdf2_sha256${tampered_token}"

    assert not password_provider.verify_password(password=password, password_hash=tampered_hash)


def test_validate_password_success(password_provider: PasswordProvider) -> None:
    """
    Returns True when password meets all complexity requirements.
    """
    password = "Abc1234*"
    assert password_provider.validate_password(password=password)


@pytest.mark.parametrize(
    "password",
    [
        "short1!",
        "alllowercase1!",
        "ALLUPPERCASE1!",
        "NoDigitsHere!",
        "NoSpecial123",
    ],
)
def test_validate_password_failure(password_provider: PasswordProvider, password: str) -> None:
    """
    Returns False when password is missing any required character class or minimum length.
    """
    assert not password_provider.validate_password(password=password)


