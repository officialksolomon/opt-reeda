from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User
from django.core.exceptions import ObjectDoesNotExist


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """

from django import forms
from .models import UserSettings

class UserUpdateForm(forms.ModelForm):
    audio_speed = forms.DecimalField(
        label=_("Audio Playback Speed"),
        max_digits=3, 
        decimal_places=2,
        required=False,
        widget=forms.Select(choices=UserSettings.audio_speed.field.choices)
    )

    class Meta:
        model = User
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                self.fields['audio_speed'].initial = self.instance.settings.audio_speed
            except ObjectDoesNotExist:
                self.fields['audio_speed'].initial = 1.00

    def save(self, commit=True):
        user = super().save(commit=commit)
        if 'audio_speed' in self.cleaned_data:
            settings, _ = UserSettings.objects.get_or_create(user=user)
            settings.audio_speed = self.cleaned_data['audio_speed']
            if commit:
                settings.save()
        return user
