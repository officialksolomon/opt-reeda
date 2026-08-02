from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    class Meta:
        model = User
        fields = ("pk", "username", "email", "name")
        read_only_fields = ("email",)
