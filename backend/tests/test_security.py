import pytest

from app.core.security import create_access_token, hash_password, verify_password


def test_password_hash_and_verify_roundtrip():
    stored = hash_password("s3cret!")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret!", stored)
    assert not verify_password("wrong", stored)


def test_password_verify_rejects_garbage():
    assert not verify_password("x", "not-a-hash")
    assert not verify_password("x", "")


def test_token_roundtrip():
    token = create_access_token("user-1", "alice", "analyst")
    payload = decode(token)
    assert payload["sub"] == "user-1"
    assert payload["username"] == "alice"
    assert payload["role"] == "analyst"


def test_token_rejects_tampering():
    from app.core.security import TokenError, decode_access_token

    token = create_access_token("user-1", "alice", "analyst")
    tampered = token[:-2] + ("ab" if not token.endswith("ab") else "cd")
    with pytest.raises(TokenError):
        decode_access_token(tampered)


def decode(token):
    from app.core.security import decode_access_token

    return decode_access_token(token)
