"""
Celery tasks for authentication.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_otp_email_task(email, otp_code, otp_type):
    """
    Celery async task to send OTP email.
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


class SendOTPEmail:
    """
    OTP Email sender wrapper.
    Tries Celery async first, falls back to sync if Redis unavailable.
    """
    
    def delay(self, email, otp_code, otp_type):
        """
        Send OTP email - async with Celery or sync fallback.
        """
        try:
            # Try async with Celery
            return send_otp_email_task.delay(email, otp_code, otp_type)
        except Exception as e:
            # Redis not available, send synchronously
            print(f"Celery/Redis unavailable, sending email synchronously: {e}")
            return send_otp_email_task(email, otp_code, otp_type)


# Create instance - use this in views
send_otp_email = SendOTPEmail()