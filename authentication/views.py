"""
Views for authentication endpoints.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate

from core.responses import success_response, error_response, created_response
from core.utils import generate_otp, get_otp_expiry, generate_uuid
from .models import User, OTP, PasswordResetToken
from .serializers import (
    RegisterSerializer, SuperAdminRegisterSerializer, LoginSerializer,
    OTPSerializer, ResendOTPSerializer, PasswordResetRequestSerializer,
    PasswordResetSerializer, ChangePasswordSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer, LogoutSerializer
)
from .tasks import send_otp_email


class RegisterSuperAdminView(APIView):
    """
    Register super admin account.
    POST /api/auth/register-superadmin/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Registration failed", serializer.errors)
        
        user = serializer.save()
        
        # Generate and send OTP
        otp_code = generate_otp()
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type='registration',
            expires_at=get_otp_expiry()
        )
        
        # Send OTP email (async)
        
        send_otp_email.delay(user.email, otp_code, 'registration')
        
        return created_response(
            "Super admin registered successfully. OTP sent to your email.",
            {
                'user_id': str(user.id),
                'email': user.email,
                'role': user.role,
                'otp_expires_at': otp.expires_at.isoformat()
            }
        )

class RegisterView(APIView):
    """
    Register new user.
    POST /api/auth/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Registration failed", serializer.errors)
        
        user = serializer.save()
        
        # Generate OTP
        otp_code = generate_otp()
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type='registration',
            expires_at=get_otp_expiry()
        )
        
        # Send OTP email (synchronous - no Celery required)
        send_otp_email.delay(user.email, otp_code, 'registration')
        
        return created_response(
            "Registration successful. OTP sent to your email.",
            {
                'user_id': str(user.id),
                'email': user.email,
                'otp_expires_at': otp.expires_at.isoformat()
            }
        )


class ResendOTPView(APIView):
    """
    Resend OTP to email.
    POST /api/auth/resend-otp/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        email = serializer.validated_data['email']
        otp_type = serializer.validated_data['otp_type']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("User not found", status_code=404)
        
        # Invalidate old OTPs
        OTP.objects.filter(user=user, otp_type=otp_type, is_used=False).update(is_used=True)
        
        # Generate new OTP
        otp_code = generate_otp()
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            expires_at=get_otp_expiry()
        )
        
        # Send OTP email (synchronous)
        send_otp_email.delay(user.email, otp_code, otp_type)
        
        return success_response(
            "OTP resent successfully",
            {
                'email': user.email,
                'otp_expires_at': otp.expires_at.isoformat()
            }
        )


class VerifyOTPView(APIView):
    """
    Verify OTP code.
    POST /api/auth/verify-otp/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        otp_type = serializer.validated_data['otp_type']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("User not found", status_code=404)
        
        try:
            otp = OTP.objects.get(
                user=user,
                otp_code=otp_code,
                otp_type=otp_type,
                is_used=False
            )
        except OTP.DoesNotExist:
            return error_response("Invalid OTP code")
        
        if not otp.is_valid():
            return error_response("OTP has expired")
        
        otp.is_used = True
        otp.save()
        
        if otp_type == 'registration':
            user.is_verified = True
            user.save()
            return success_response(
                "Email verified successfully",
                {'email': user.email, 'is_verified': True}
            )
        
        return success_response(
            "OTP verified successfully",
            {'email': user.email}
        )


class LoginView(APIView):
    """
    User login.
    POST /api/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        
        user = authenticate(email=email, password=password)
        
        if not user:
            return error_response(
                "Invalid credentials",
                {"detail": "Email or password is incorrect"},
                status_code=401
            )
        
        if not user.is_active:
            return error_response(
                "Account disabled",
                {"detail": "Your account has been disabled"},
                status_code=401
            )
        
        if not user.is_verified:
            return error_response(
                "Email not verified",
                {"detail": "Please verify your email first"},
                status_code=401
            )
            
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        profile_url = None
        if user.profile_picture:
            profile_url = request.build_absolute_uri(user.profile_picture.url)
        
        return success_response(
            "Login successful",
            {
                'user': {
                    'user_id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'phone':user.phone_number,
                    'role': user.role,
                    'profile_picture': profile_url,
                    'is_verified': user.is_verified
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        )


class LogoutView(APIView):
    """
    Logout user and blacklist refresh token.
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return success_response("Logout successful")
        except TokenError:
            return error_response("Invalid token")


class PasswordResetRequestView(APIView):
    """
    Request password reset OTP.
    POST /api/auth/password-reset-request/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists
            return success_response(
                "Password reset OTP sent to your email",
                {'email': email}
            )
        
        # Generate OTP
        otp_code = generate_otp()
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type='password_reset',
            expires_at=get_otp_expiry()
        )
        
        # Send OTP email (synchronous)
        send_otp_email.delay(user.email, otp_code, 'password_reset')
        
        return success_response(
            "Password reset OTP sent to your email",
            {
                'email': user.email,
                'otp_expires_at': otp.expires_at.isoformat()
            }
        )


class VerifyResetOTPView(APIView):
    """
    Verify password reset OTP and get reset token.
    POST /api/auth/verify-reset-otp/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        
        if not email or not otp_code:
            return error_response("Email and OTP code are required")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("User not found", status_code=404)
        
        try:
            otp = OTP.objects.get(
                user=user,
                otp_code=otp_code,
                otp_type='password_reset',
                is_used=False
            )
        except OTP.DoesNotExist:
            return error_response("Invalid OTP code")
        
        if not otp.is_valid():
            return error_response("OTP has expired")
        
        otp.is_used = True
        otp.save()
        
        # Create reset token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=generate_uuid(),
            expires_at=get_otp_expiry(minutes=15)
        )
        
        return success_response(
            "OTP verified successfully",
            {
                'reset_token': reset_token.token,
                'expires_at': reset_token.expires_at.isoformat()
            }
        )


class PasswordResetView(APIView):
    """
    Reset password with verified token.
    POST /api/auth/password-reset/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("User not found", status_code=404)
        
        user.set_password(new_password)
        user.save()
        
        # Invalidate all reset tokens
        PasswordResetToken.objects.filter(user=user).update(is_used=True)
        
        return success_response("Password reset successful. Please login with your new password.")


class ChangePasswordView(APIView):
    """
    Change password for logged-in user.
    POST /api/auth/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return error_response("Invalid old password")
        
        user.set_password(new_password)
        user.save()
        
        return success_response("Password changed successfully")


class TokenRefreshView(APIView):
    """
    Refresh access token.
    POST /api/auth/token-refresh/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return error_response("Refresh token is required")
        
        try:
            refresh = RefreshToken(refresh_token)
            return success_response(
                "Token refreshed",
                {'access': str(refresh.access_token)}
            )
        except TokenError:
            return error_response("Invalid or expired token", status_code=401)


class ProfileView(APIView):
    """
    Get and update user profile.
    GET /api/auth/profile/
    PATCH /api/auth/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return success_response("Profile retrieved", serializer.data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = serializer.save()
        profile_serializer = UserProfileSerializer(user, context={'request': request})
        
        return success_response("Profile updated successfully", profile_serializer.data)