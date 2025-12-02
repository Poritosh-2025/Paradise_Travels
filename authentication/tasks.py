"""
Celery tasks for authentication.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_otp_email(email, otp_code, otp_type):
    """
    Send OTP to user email asynchronously.
    """
    if otp_type == 'registration':
        subject = 'Email Verification OTP'
        message = f'''
Hello,

Your email verification OTP is: {otp_code}

This OTP will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you did not request this, please ignore this email.

Best regards,
Admin API Team
        '''
    else:
        subject = 'Password Reset OTP'
        message = f'''
Hello,

Your password reset OTP is: {otp_code}

This OTP will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you did not request this, please ignore this email.

Best regards,
Admin API Team
        '''
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
