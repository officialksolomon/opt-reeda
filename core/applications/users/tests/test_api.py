from typing import Any

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User: Any = get_user_model()


class AuthAPITests(APITestCase):
    client: Any

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123",  # noqa: S106
            name="Test User",
        )
        EmailAddress.objects.create(
            user=self.user,
            email="testuser@example.com",
            primary=True,
            verified=True,
        )
        self.login_url = "/api/auth/login/"
        self.refresh_url = "/api/auth/token/refresh/"
        self.user_url = "/api/auth/user/"
        self.registration_url = "/api/auth/registration/"

    def test_login_obtains_jwt(self):
        data = {"username": "testuser", "password": "testpassword123"}
        response = self.client.post(self.login_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["username"] == "testuser"

    def test_jwt_refresh(self):
        # First login to get a valid refresh token
        data = {"username": "testuser", "password": "testpassword123"}
        login_resp = self.client.post(self.login_url, data)
        refresh_token = login_resp.data["refresh"]

        # Now refresh it
        refresh_data = {"refresh": refresh_token}
        refresh_resp = self.client.post(self.refresh_url, refresh_data)
        assert refresh_resp.status_code == status.HTTP_200_OK
        assert "access" in refresh_resp.data

    def test_user_profile_retrieval(self):
        login_data = {"username": "testuser", "password": "testpassword123"}
        login_resp = self.client.post(self.login_url, login_data)
        access_token = login_resp.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.user_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"
        assert response.data["name"] == "Test User"

    def test_user_registration(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "newpassword123",
            "password2": "newpassword123",
        }
        response = self.client.post(self.registration_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username="newuser").exists()
        assert "Verification e-mail sent." in response.data.get("detail", "")
