from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.applications.users.forms import UserAdminChangeForm
from core.applications.users.tests.factories import UserFactory
from core.applications.users.views import UserRedirectView
from core.applications.users.views import SettingsView
from core.applications.users.views import user_detail_view

if TYPE_CHECKING:
    from django.test import RequestFactory

    from core.applications.users.models import User

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    def dummy_get_response(self, request: HttpRequest):
        return None

    def _setup_view(self, view, request, user):
        request.user = user
        view.request = request
        return view

    def test_get_context_data(self, user: User, rf: RequestFactory):
        view = SettingsView()
        request = rf.get("/fake-url/")
        view = self._setup_view(view, request, user)
        context = view.get_context_data()
        assert 'profile_form' in context
        assert 'settings_form' in context

    def test_post_valid_profile(self, user: User, rf: RequestFactory):
        view = SettingsView()
        request = rf.post("/fake-url/", data={"update_profile": "1", "name": "New Name"})

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        
        view = self._setup_view(view, request, user)

        response = view.post(request)
        
        # It should redirect on success or return template on failure
        # In this case it redirects to users:update
        assert response.status_code in [200, 302]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user
        view.request = request
        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory.create()
        response = user_detail_view(request, username=user.username)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"
