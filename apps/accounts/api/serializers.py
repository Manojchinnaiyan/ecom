from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import User, Address, UserProfile


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for user addresses.
    """

    class Meta:
        model = Address
        fields = [
            "id",
            "address_type",
            "default",
            "full_name",
            "street_address1",
            "street_address2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        """
        Automatically set the user from the request.
        """
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profiles.
    """

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "bio",
            "preferences",
            "marketing_opt_in",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for users.
    """

    addresses = AddressSerializer(many=True, read_only=True)
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
            "profile_image",
            "addresses",
            "profile",
            "password",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def create(self, validated_data):
        """
        Create a new user with encrypted password and return it.
        """
        password = validated_data.pop("password", None)
        user = super().create(validated_data)

        if password:
            user.set_password(password)
            user.save()

        # Create user profile
        UserProfile.objects.create(user=user)

        return user

    def update(self, instance, validated_data):
        """
        Update user details, handling password update specially.
        """
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs):
        """
        Validate that passwords match.
        """
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """
        Create new user with encrypted password and return it.
        """
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # Create user profile
        UserProfile.objects.create(user=user)

        return user


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate current password is correct and new passwords match.
        """
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "New passwords do not match."}
            )

        return attrs
