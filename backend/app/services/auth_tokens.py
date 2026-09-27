"""Bearer-token issuance for user-scoped routes.

Not a full auth system — resumes are uploaded anonymously and get an opaque
token that must be presented on subsequent user-scoped calls. This closes the
"guess a ULID, edit someone else's profile" hole. A real deployment swaps this
for OAuth/OIDC + session cookies, but the API shape stays the same.
"""
from __future__ import annotations

import secrets
from typing import Protocol


class TokenStore(Protocol):
    def issue(self, user_id: str) -> str: ...
    def resolve(self, token: str) -> str | None: ...
    def revoke(self, token: str) -> bool: ...


class InMemoryTokenStore:
    def __init__(self) -> None:
        self._token_to_user: dict[str, str] = {}

    def issue(self, user_id: str) -> str:
        # 32-byte URL-safe token (~43 chars). Sufficient entropy for opaque bearer.
        token = secrets.token_urlsafe(32)
        self._token_to_user[token] = user_id
        return token

    def resolve(self, token: str) -> str | None:
        return self._token_to_user.get(token)

    def revoke(self, token: str) -> bool:
        return self._token_to_user.pop(token, None) is not None
