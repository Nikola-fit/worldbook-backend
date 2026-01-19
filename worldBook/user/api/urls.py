from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from user.api.views import registration_view
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .serializers import CustomTokenObtainPairView

urlpatterns = [
    path("registration", registration_view, name="registration"),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
