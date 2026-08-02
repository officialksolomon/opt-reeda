from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from django.db import models

if TYPE_CHECKING:
    Model = models.Model
else:
    import auto_prefetch

    Model = auto_prefetch.Model


class TimeBasedModel(Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        objects: ClassVar[models.Manager[Any]]
        prefetch_manager: ClassVar[models.Manager[Any]]

    class Meta(Model.Meta if not TYPE_CHECKING else object):  # type: ignore[misc]
        abstract = True
