# Django Admin API

A production-level Django REST Framework application with authentication, user management, administrator management, payment processing, and API key management.

## Features

- **JWT Authentication** - Secure token-based authentication
- **Email OTP Verification** - Email verification for registration and password reset
- **Role-Based Access Control** - User, Staff Admin, Super Admin roles
- **User Management** - Admin can manage, enable/disable, delete users
- **Administrator Management** - Super admin can manage staff admins
- **Stripe Payment Integration** - Subscription payments with Stripe
- **API Key Management** - Manage external API keys
- **Celery Async Tasks** - Asynchronous email sending

## Project Structure

```
django_admin_api/
├── manage.py
├── requirements.txt
├── .env.example
├── root/                   # Main project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
├── core/                   # Shared utilities
│   ├── __init__.py
│   ├── apps.py
│   ├── permissions.py
│   ├── responses.py
│   ├── pagination.py
│   └── utils.py
├── authentication/         # User authentication
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── tasks.py
│   └── admin.py
├── dashboard/              # Dashboard statistics
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── user_management/        # User management
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── administrators/         # Administrator management
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── payments/              # Stripe payments
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
└── api_management/        # API key management
    ├── __init__.py
    ├── apps.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    └── admin.py
```

## Setup Instructions

### Step 1: Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your settings
```

### Step 3: Create MySQL Database

```sql
CREATE DATABASE admin_api_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 4: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Create Super Admin

```bash
python manage.py createsuperuser
```

### Step 6: Run Development Server

```bash
python manage.py runserver
```

### Step 7: Run Celery Worker (for async emails)

```bash
# In a new terminal
celery -A root worker -l info
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register-superadmin/` | Register super admin |
| POST | `/api/auth/register/` | User registration |
| POST | `/api/auth/resend-otp/` | Resend OTP |
| POST | `/api/auth/verify-otp/` | Verify OTP |
| POST | `/api/auth/login/` | User login |
| POST | `/api/auth/logout/` | User logout |
| POST | `/api/auth/password-reset-request/` | Request password reset |
| POST | `/api/auth/verify-reset-otp/` | Verify reset OTP |
| POST | `/api/auth/password-reset/` | Reset password |
| POST | `/api/auth/change-password/` | Change password |
| POST | `/api/auth/token-refresh/` | Refresh access token |
| GET | `/api/auth/profile/` | Get user profile |
| PATCH | `/api/auth/profile/` | Update user profile |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/statistics/` | Get dashboard statistics |

### User Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user-management/users/` | List all users |
| POST | `/api/user-management/users/{id}/disable/` | Disable user |
| POST | `/api/user-management/users/{id}/enable/` | Enable user |
| POST | `/api/user-management/users/{id}/delete-request/` | Request deletion |
| POST | `/api/user-management/users/{id}/delete-confirm/` | Confirm deletion |
| POST | `/api/user-management/users/{id}/delete-cancel/` | Cancel deletion |

### Administrators
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/administrators/admins/` | List all admins |
| POST | `/api/administrators/admins/create/` | Create staff admin |
| PATCH | `/api/administrators/admins/{id}/` | Update admin |
| POST | `/api/administrators/admins/{id}/disable/` | Disable admin |
| POST | `/api/administrators/admins/{id}/enable/` | Enable admin |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/payments/transactions/` | List transactions |
| POST | `/api/payments/create-intent/` | Create payment intent |
| POST | `/api/payments/confirm/` | Confirm payment |
| POST | `/api/payments/webhook/` | Stripe webhook |

### API Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/api-management/key/` | View API key |
| POST | `/api/api-management/key/update/` | Update API key |
| DELETE | `/api/api-management/key/{id}/` | Delete API key |

## User Roles

1. **User** - Regular user with limited access
2. **Staff Admin** - Can manage users and view dashboard
3. **Super Admin** - Full access to all features

## Gmail App Password Setup

1. Go to Google Account Settings
2. Security → 2-Step Verification (enable if not)
3. App passwords → Generate new password
4. Use this 16-character password in `EMAIL_HOST_PASSWORD`

## Testing with Postman

1. Register a super admin first
2. Login to get access token
3. Add header: `Authorization: Bearer <access_token>`
4. Test all endpoints

## Common Issues

### PyMySQL Error
Make sure `pymysql.install_as_MySQLdb()` is in `root/__init__.py`

### Celery Not Sending Emails
1. Start Redis server: `redis-server`
2. Start Celery worker: `celery -A root worker -l info`

### CORS Issues
Add your frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`

## License

MIT License
