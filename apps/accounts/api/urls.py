# apps/accounts/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import UserViewSet, UserRegistrationView, AddressViewSet, UserProfileViewSet

# Create a router for viewsets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"addresses", AddressViewSet, basename="address")
router.register(r"profiles", UserProfileViewSet, basename="profile")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Authentication endpoints
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
