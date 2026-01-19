from django.utils import timezone
from rest_framework import serializers
from user.models import User
import re
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class UserSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password_confirm"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        password = data.get("password")
        password_confirm = data.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        if len(password) < 8:
            raise serializers.ValidationError(
                {"password": "Password must be at least 8 characters long."}
            )

        if not re.search(r"\d", password):
            raise serializers.ValidationError(
                {"password": "Password must contain at least one digit."}
            )

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise serializers.ValidationError(
                {"password": "Password must contain at least one special character."}
            )

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")  # Remove password_confirm before saving
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],  # Automatically hashes password
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username  # Using `username` from `AbstractUser`
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
