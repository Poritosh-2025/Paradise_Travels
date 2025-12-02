"""
Serializers for administrators endpoints.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from authentication.models import User


class AdminListSerializer(serializers.ModelSerializer):
    """
    Serializer for admin list.
    """
    admin_id = serializers.UUIDField(source='id')
    admin_name = serializers.CharField(source='name')
    admin_email = serializers.EmailField(source='email')
    admin_contact_number = serializers.CharField(source='phone_number')
    has_access_to = serializers.CharField(source='role')

    class Meta:
        model = User
        fields = [
            'admin_id', 'admin_name', 'admin_email',
            'admin_contact_number', 'has_access_to',
            'is_active', 'created_at'
        ]


class CreateStaffAdminSerializer(serializers.Serializer):
    """
    Serializer for creating staff admin.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=['staff_admin'], default='staff_admin')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'staff_admin'),
            is_staff=True,
            is_verified=True
        )
        return user


class UpdateAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for updating admin profile.
    """
    class Meta:
        model = User
        fields = ['name', 'email', 'phone_number', 'role', 'profile_picture']

    def validate_email(self, value):
        admin = self.instance
        if User.objects.exclude(id=admin.id).filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value.lower()

    def validate_role(self, value):
        # Only allow changing to staff_admin (super_admin is protected)
        if value not in ['staff_admin', 'super_admin']:
            raise serializers.ValidationError("Invalid role")
        return value
