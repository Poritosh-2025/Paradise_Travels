"""
Serializers for authentication endpoints.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from payments.models import UsageTracking, VideoPurchase
from .models import User


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    
    New Logic:
    - Only block if email exists AND is verified
    - Allow re-registration for unverified emails
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    re_type_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        email = value.lower()
        # Only block if user exists AND is verified
        if User.objects.filter(email=email, is_verified=True).exists():
            raise serializers.ValidationError("User with this email already exists")
        return email

    def validate(self, data):
        if data['password'] != data['re_type_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data

    def create(self, validated_data):
        validated_data.pop('re_type_password')
        email = validated_data['email']
        password = validated_data['password']
        
        # Check for existing unverified user
        existing_user = User.objects.filter(email=email, is_verified=False).first()
        
        if existing_user:
            # Update existing unverified user's password
            existing_user.set_password(password)
            existing_user.save()
            return existing_user
        
        # Create new user
        return User.objects.create_user(**validated_data)


class SuperAdminRegisterSerializer(RegisterSerializer):
    """
    Serializer for super admin registration.
    """
    def create(self, validated_data):
        validated_data.pop('re_type_password')
        validated_data['role'] = 'super_admin'
        validated_data['is_staff'] = True
        validated_data['is_verified'] = True
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification.
    """
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    otp_type = serializers.ChoiceField(choices=['registration', 'password_reset'])


class ResendOTPSerializer(serializers.Serializer):
    """
    Serializer for resending OTP.
    """
    email = serializers.EmailField()
    otp_type = serializers.ChoiceField(choices=['registration', 'password_reset'])


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for password reset.
    """
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing password.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    re_type_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['re_type_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    """
    user_id = serializers.UUIDField(source='id', read_only=True)
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'user_id', 'name', 'email', 'phone_number', 'role',
            'profile_picture', 'is_verified', 'is_active',
            'subscription_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user_id', 'role', 'is_verified', 'is_active', 'subscription_status', 'created_at', 'updated_at']

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['is_subscriber'] = instance.is_subscriber
        can_generate_video = False
        if UsageTracking.objects.filter(user=instance, videos_remaining__gt=0).exists():
            can_generate_video = True
        if VideoPurchase.objects.filter(user=instance, generation_status__in=["pending", "processing"]).exists():
            can_generate_video = True

        ret['can_generate_video'] = can_generate_video
        return ret

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    """
    class Meta:
        model = User
        fields = ['name', 'email', 'phone_number', 'profile_picture']

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(id=user.id).filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value.lower()


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout.
    """
    refresh = serializers.CharField()


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for token refresh.
    """
    refresh = serializers.CharField()
