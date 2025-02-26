# apps/accounts/api/views.py
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.accounts.models import Address, UserProfile
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    AddressSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
)
from utils.permissions import IsOwnerOrAdmin

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Restrict queryset to the current user unless staff.
        """
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        Get current user's profile.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def change_password(self, request):
        """
        Change user's password.
        """
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response(
                {"detail": "Password changed successfully."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(
                    user, context=self.get_serializer_context()
                ).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class AddressViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user addresses.
    """

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return addresses for the current user.
        """
        return Address.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def shipping(self, request):
        """
        Get user's shipping addresses.
        """
        addresses = Address.objects.filter(user=request.user, address_type="shipping")
        serializer = self.get_serializer(addresses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def billing(self, request):
        """
        Get user's billing addresses.
        """
        addresses = Address.objects.filter(user=request.user, address_type="billing")
        serializer = self.get_serializer(addresses, many=True)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user profiles.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Return profile for the current user.
        """
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Get the profile for the current user.
        """
        return UserProfile.objects.get(user=self.request.user)
