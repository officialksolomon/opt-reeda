from __future__ import annotations

from typing import Any

from factory.django import DjangoModelFactory
from factory.faker import Faker
from factory.helpers import post_generation

from core.applications.users.models import User


class UserFactory(DjangoModelFactory[User]):
    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self: Any, create: bool, extracted: str | None, **kwargs: Any):  # noqa: FBT001
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)
        if create:
            self.save()

    class Meta:  # pyright: ignore[reportAssignmentType]
        model = User
        django_get_or_create = ["username"]
        skip_postgeneration_save = True
