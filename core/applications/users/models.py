from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, BooleanField, IntegerField, DecimalField, DateTimeField, OneToOneField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from typing import TYPE_CHECKING
from core.helpers.models import TimeBasedModel

if TYPE_CHECKING:
    from django.db.models import ForeignKey
else:
    import auto_prefetch
    ForeignKey = auto_prefetch.ForeignKey



class User(AbstractUser):
    """
    Default custom user model for My Awesome Project.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


