from __future__ import annotations

from typing import Any


def test_user_get_absolute_url(user: Any):
    assert user.get_absolute_url() == f"/users/{user.username}/"
