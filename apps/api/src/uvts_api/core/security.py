import hashlib
import secrets


def generate_session_token() -> str:
    """Return an opaque token with enough entropy to be an anonymous credential."""

    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash the credential so a database read does not reveal usable cookies."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
