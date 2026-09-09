from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, BooleanField, IntegerField, DecimalField, DateTimeField, OneToOneField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from typing import TYPE_CHECKING
from core.helpers.models import TimeBasedModel
from core.helpers.enums import ChunkSize, TTSVoice

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

    free_tries_used = IntegerField(default=0)

    @property
    def audio_speed_pref(self) -> float:
        try:
            return float(self.settings.audio_speed)
        except ObjectDoesNotExist:
            return 1.00

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


class UserSettings(TimeBasedModel):
    user = OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="settings"
    )
    audio_speed = DecimalField(
        _("Audio Playback Speed"),
        max_digits=3,
        decimal_places=2,
        default=1.00,
        choices=[
            (0.50, '0.5x - Very Slow'),
            (0.75, '0.75x - Slow'),
            (1.00, '1.0x - Normal'),
            (1.25, '1.25x - Fast'),
            (1.50, '1.5x - Very Fast'),
            (2.00, '2.0x - Extremely Fast')
        ]
    )
    
    # Audio & Playback
    default_voice = CharField(
        _("Default TTS Voice"), 
        max_length=50, 
        choices=TTSVoice.choices,
        default=TTSVoice.ALLOY
    )
    voice_pitch = DecimalField(_("Voice Pitch"), max_digits=3, decimal_places=2, default=1.00)
    voice_volume = DecimalField(_("Voice Volume"), max_digits=3, decimal_places=2, default=1.00)
    auto_play = BooleanField(_("Auto-Play Audio"), default=False)
    visual_highlight_style = CharField(
        _("Highlight Style"), 
        max_length=20, 
        default="bg-yellow-200",
        choices=[
            ("bg-yellow-200", "Yellow Background"),
            ("bg-brand/20", "Red Background"),
            ("underline", "Underline"),
            ("text-brand font-bold", "Bold Text")
        ]
    )
    
    # UI, Accessibility & Display
    theme_preference = CharField(
        _("App Theme"), 
        max_length=20, 
        default="system",
        choices=[
            ("light", "Light Mode"),
            ("dark", "Dark Mode"),
            ("system", "System Default")
        ]
    )
    font_size = CharField(
        _("Reading Font Size"), 
        max_length=20, 
        default="medium",
        choices=[
            ("text-sm", "Small"),
            ("text-base", "Medium"),
            ("text-lg", "Large"),
            ("text-xl", "Extra Large")
        ]
    )
    font_family = CharField(
        _("Reading Font Family"), 
        max_length=50, 
        default="sans",
        choices=[
            ("font-sans", "Sans-Serif (Default)"),
            ("font-serif", "Serif"),
            ("font-mono", "Monospace (Dyslexia Friendly)")
        ]
    )
    layout_density = CharField(
        _("Layout Density"), 
        max_length=20, 
        default="comfortable",
        choices=[
            ("compact", "Compact"),
            ("comfortable", "Comfortable")
        ]
    )
    reduce_motion = BooleanField(_("Reduce Motion"), default=False)
    
    # Document Processing
    chunk_size = CharField(
        _("Document Chunk Size"),
        max_length=10,
        choices=ChunkSize.choices,
        default=ChunkSize.MEDIUM,
    )
    
    # Account Settings
    email_notifications = BooleanField(_("Email Notifications"), default=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("User Settings")
        verbose_name_plural = _("User Settings")

    def __str__(self) -> str:
        return f"Settings for {self.user.username}"
