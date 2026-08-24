from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from core.applications.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


from core.applications.users.forms import UserProfileForm, UserSettingsForm
from core.applications.users.models import UserSettings
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages

class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "users/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        
        if 'profile_form' not in context:
            context['profile_form'] = UserProfileForm(instance=user)
        if 'settings_form' not in context:
            context['settings_form'] = UserSettingsForm(instance=settings_obj)
            
        return context

    def post(self, request, *args, **kwargs):
        user = self.request.user
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        
        profile_form = UserProfileForm(instance=user)
        settings_form = UserSettingsForm(instance=settings_obj)

        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _("Profile updated successfully."))
                return redirect("users:update")
        elif 'update_settings' in request.POST:
            settings_form = UserSettingsForm(request.POST, instance=settings_obj)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, _("Settings updated successfully."))
                return redirect("users:update")

        return self.render_to_response(self.get_context_data(
            profile_form=profile_form,
            settings_form=settings_form
        ))


user_update_view = SettingsView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()

from allauth.account.models import EmailConfirmationHMAC, EmailConfirmation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema

class VerifyEmailConfirmView(APIView):
    permission_classes = (AllowAny,)
    
    @extend_schema(responses=None)
    def get(self, request, key):
        try:
            confirmation = EmailConfirmationHMAC.from_key(key)
            if not confirmation:
                confirmation = EmailConfirmation.objects.get(key=key.lower())
            
            confirmation.confirm(self.request)
            return Response({"detail": "Email confirmed successfully."}, status=200)
        except EmailConfirmation.DoesNotExist:
            return Response({"detail": "Email confirmation not found."}, status=404)
        except Exception:
            return Response({"detail": "Invalid or expired key."}, status=400)
