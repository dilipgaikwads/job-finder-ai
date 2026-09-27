"""Profile storage — in-memory for Phase 4 scaffold. Swap for Postgres later."""
from __future__ import annotations

from typing import Protocol

from app.models.profile import Profile


class ProfileStore(Protocol):
    def put(self, profile: Profile) -> str: ...
    def get(self, user_id: str) -> Profile | None: ...
    def all(self) -> list[Profile]: ...
    def delete(self, user_id: str) -> bool: ...


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._by_user: dict[str, Profile] = {}

    def put(self, profile: Profile) -> str:
        self._by_user[profile.user_id] = profile
        return profile.user_id

    def get(self, user_id: str) -> Profile | None:
        return self._by_user.get(user_id)

    def all(self) -> list[Profile]:
        return list(self._by_user.values())

    def delete(self, user_id: str) -> bool:
        return self._by_user.pop(user_id, None) is not None
