"""
Tests for portal.providers.password_provider.PasswordProvider
"""
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


