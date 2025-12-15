# Paradise Travels (Django)

Comprehensive project README for the Paradise Travels backend application.

**Project**: Paradise_Travels

**Location**: `/home/betopia/poritosh/Office_project/Paradise`

## Overview

This is a Django REST API backend for Paradise Travels. It includes user management, authentication, payments (Stripe integration), administrative endpoints, and background task support. The project uses Django, Django REST Framework and Stripe for payment processing.

Key apps in the repository:
- `authentication` — login / registration and auth-related APIs
- `user_management` — user profiles and management
- `payments` — Stripe integration, payment intents, confirmations, and webhook handling
- `dashboard` — admin-facing dashboards and endpoints
- `api_management` — general API models/serializers used across the project
- `administrators` — admin user utilities and API
- `core` — shared utilities, responses, pagination and permissions

## Repository Layout

Top-level files and folders (important ones):

- `manage.py` — Django management entrypoint
- `run.sh` — helper script to run the app (project-specific)
- `requirements.txt` — Python dependencies
- `root/` — Django project settings and ASGI/WGI/Celery configs
- `payments/` — payment-related models, serializers and views
- `celerybeat-schedule` — Celery schedule file (if Celery is used)
- `db.sqlite3` — example local sqlite DB (if present)
## Standard Project README — Detailed Reference

This README provides a single, opinionated, standard documentation for running, configuring, testing and maintaining the project. It is designed to be a single source of truth for developers and operators.

Table of contents
- Project overview
- Quickstart (local)
- Environment variables (`.env`)
- Install & Run (detailed)
- Project layout and important files
- App-by-app summary (models & serializers)
- Key endpoints and example payloads
- API testing (Postman + examples)
- Webhooks and integrations
- Troubleshooting and common issues
- Contributing and development notes

## Project overview

Paradise Travels is a Django REST API backend that provides authentication, user management, admin dashboards, Stripe-based payments (subscriptions and purchases), API key management, and asynchronous tasks (Celery). It uses a custom `User` model with email-based authentication and JWT tokens for API auth.

## Quickstart (local)

1. Copy environment example and fill secrets:

```bash
cp .env.example .env
# Edit .env and fill in real values
```

2. Create and activate a virtual environment, install dependencies, run migrations, create a superuser and start the server:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:9001
```

3. (Optional) Start Celery worker and beat:

```bash

source .venv/bin/activate
celery -A root worker -l info
celery -A root beat -l info
```

`run.sh` is a helper script that can open new terminals and start Django, Celery worker and Celery beat (customize paths in the script).

## Environment variables (`.env` / `.env.example`)

The project loads environment variables via `python-dotenv` / `decouple`. Key variables used by `root/settings.py` are:

- `SECRET_KEY` or `DJANGO_SECRET_KEY`: Django secret key
- `DEBUG`: `True` or `False`
- `ALLOWED_HOSTS`: comma-separated hosts

- Database (example): `DATABASE_ENGINE`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`

- Stripe:
    - `STRIPE_SECRET_KEY`
    - `STRIPE_PUBLISHABLE_KEY`
    - `STRIPE_WEBHOOK_SECRET`
    - `STRIPE_PREMIUM_PRICE_ID`, `STRIPE_PRO_PRICE_ID`, `STRIPE_VIDEO_PRICE_ID`

- Email / SMTP:
    - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`

- Celery / Redis:
    - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

You can find a ready file at `.env.example` in the repository root. Never commit real secrets to Git.

## Install & Run (detailed)

1. Create virtual environment and install packages (see `requirements.txt`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure `.env` with DB and service credentials.

3. If using PostgreSQL or MySQL, create the database and update `.env` accordingly. By default the project runs on `sqlite3` (local `db.sqlite3`).

4. Run migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

5. Start the development server:

```bash
python manage.py runserver 0.0.0.0:9001
```

6. Start Celery (if required):

```bash
celery -A root worker -l info
celery -A root beat -l info
```

## Project layout and important files

Top-level files
- `manage.py` — Django CLI entrypoint.
- `requirements.txt` — Python dependencies.
- `.env.example` — Example environment variables (placeholders).
- `run.sh` — Convenience script to start services in new terminals.
- `db.sqlite3` — Local database (if used).
- `docs/` — Postman collection and documentation artifacts.

Project packages (each app folder contains `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py` where applicable):
- `root/` — Project configuration, `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `celery.py`.
- `core/` — Shared utilities (`responses.py`, `permissions.py`, `pagination.py`, `utils.py`).
- `authentication/` — Custom `User` model, OTPs, registration, login, password reset and JWT handling.
- `user_management/` — User management features (deletion requests, admin operations).
- `administrators/` — Staff and super admin management.
- `payments/` — Plans, subscriptions, payments, webhook handling and Stripe integration.
- `dashboard/` — Admin dashboard statistics and endpoints.
- `api_management/` — API key management functionality.
- `ai_services/` — AI related endpoints (if present).

Routing
- Root URL configuration is in `root/urls.py`. App-level routers are included under `/api/`:
    - `/api/auth/` (authentication)
    - `/api/payments/` (payments)
    - `/api/user-management/` (user management)
    - `/api/administrators/` (admin management)
    - `/api/api-management/` (API key management)
    - `/api/ai/` (AI services)

## App-by-app summary (models & serializers)

This section highlights the most important models and serializer fields in each app (useful for client developers):

- `authentication`:
    - Models: `User` (fields: `id`, `email`, `name`, `phone_number`, `profile_picture`, `stripe_customer_id`, `role`, `subscription_status`, `is_active`, `is_staff`, `is_verified`, `created_at`, `updated_at`), `OTP`, `PasswordResetToken`.
    - Serializers: `RegisterSerializer`, `LoginSerializer`, `UserProfileSerializer`, `PasswordResetSerializer`, `ChangePasswordSerializer`.

- `payments`:
    - Models: `Plan`, `Subscription`, `Payment`, `UsageTracking`, `WebhookEvent`, `VideoPurchase`.
    - Serializers: `PlanSerializer`, `CreateSubscriptionSerializer`, `PaymentSerializer`, `AdminTransactionSerializer`, `WebhookEventSerializer`.

- `user_management`:
    - Models: `UserDeletionRequest` (tracks requested deletion flows).

For full field lists, inspect `*/models.py` and `*/serializers.py` in each app.

## Key endpoints and example payloads

Authentication (example)
- POST `/api/auth/register/` — Register a user (body: `email`, `password`, `re_type_password`).
- POST `/api/auth/login/` — Login (body: `email`, `password`), returns JWT access/refresh tokens.
- GET `/api/auth/profile/` — Get authenticated user profile (requires `Authorization: Bearer <token>`).

Payments (example)
- POST `/api/payments/create-intent/` — Create a Stripe PaymentIntent. Body: `amount` (string/decimal), `currency` (e.g., EUR), `subscription_plan`.
- POST `/api/payments/confirm/` — Confirm payment after client-side completion. Body: `payment_intent_id`, `payment_method_id`.
- POST `/api/payments/webhook/` — Stripe webhook endpoint (CSRF exempt). Configure `STRIPE_WEBHOOK_SECRET` and point Stripe to this URL.

Example: Create Payment Intent

Request body:

```json
{
    "amount": "10.00",
    "currency": "EUR",
    "subscription_plan": "premium"
}
```

Success response:

```json
{
    "message": "Payment intent created successfully",
    "data": { "client_secret": "<...>", "payment_intent_id": "pi_...", "amount": 10.0, "currency": "EUR" }
}
```

## API testing (Postman + examples)

Import the provided Postman collection: `docs/Paradise_Postman_Collection.json`.

Steps:
1. Import collection into Postman.
2. Create an environment with `base_url` (e.g., `http://127.0.0.1:9001`) and `access_token` (set after login).
3. Run register → login → set `access_token` → test protected endpoints.

For webhook testing locally use `stripe listen` (Stripe CLI) or expose local server with `ngrok` and set the webhook endpoint and secret accordingly.

## Webhooks and integrations

- Stripe: configure in `root/settings.py` with `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Celery: broker and backend configured via `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.
- Email: SMTP settings configured in environment variables (see `.env.example`).

## Troubleshooting and common issues

- 415 Unsupported Media Type: ensure `Content-Type: application/json` when sending JSON.
- `"premium" is not a valid choice.`: the serializer uses ChoiceField; ensure you send allowed values or update serializer choices in `payments/serializers.py`.
- Stripe errors: verify keys and network connectivity. Use Stripe test keys in local/dev environment.
- Celery not processing tasks: ensure Redis is running and `CELERY_BROKER_URL` is set correctly.

## Testing

Run unit tests (if present):

```bash
python manage.py test
```

Use Postman / automated test scripts to validate endpoints. Consider adding CI to run tests automatically.

## Contributing

1. Fork and create a branch `feature/your-feature` or `fix/issue`.
2. Add tests for new behavior.
3. Run tests locally and open a pull request with a clear description.

## License & Maintainers

This repository does not include an explicit license file. Add a `LICENSE` if you intend to open-source the project. For internal projects, maintainers are the development team working in this workspace.

---

Generated and standardized README on: 2025-12-15

```bash
pip install -r requirements.txt
```

4. Set environment variables (example using a `.env` file or export):

```bash
export DJANGO_SECRET_KEY='your-secret-key'
export STRIPE_SECRET_KEY='sk_test_...'
export STRIPE_PUBLISHABLE_KEY='pk_test_...'
export STRIPE_WEBHOOK_SECRET='whsec_...'
```

5. Run migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

6. Start the development server:

```bash
python manage.py runserver
```

## Running with Docker / Production

If you plan to containerize or deploy, ensure you configure the environment variables in your deployment environment. The repository does not include a Dockerfile by default (check `run.sh` or existing deployment notes).

## Stripe Integration

The `payments` app integrates with Stripe. Important settings in `root/settings.py` and usage in `payments/views.py`:

- `stripe.api_key` is set from `settings.STRIPE_SECRET_KEY`
- `CreatePaymentIntentView` creates a `PaymentIntent` and stores a pending `Payment` record
- `ConfirmPaymentView` verifies the intent and updates the `Payment` record and user subscription
- `StripeWebhookView` handles `payment_intent.succeeded` and `payment_intent.payment_failed` events

Ensure your Stripe keys are set and `STRIPE_WEBHOOK_SECRET` is configured before enabling webhooks.

## Important Endpoints

- POST `/api/payments/create-intent/` — Create a Stripe PaymentIntent
- POST `/api/payments/confirm/` — Confirm and finalize a payment
- POST `/api/payments/webhook/` — Stripe webhook endpoint (CSRF exempt)
- GET `/api/payments/transactions/` — Admin endpoint for listing transactions (requires admin)

See `payments/views.py` for implementation details and required request fields.

### Example: Create Payment Intent (Postman)

- URL: `http://127.0.0.1:8000/api/payments/create-intent/`
- Method: `POST`
- Headers:
    - `Content-Type: application/json`
    - `Authorization: Bearer <token>` (user must be authenticated)
- Body (raw JSON):

```json
{
    "amount": "10.00",
    "currency": "EUR",
    "subscription_plan": "premium"
}
```

Notes:
- A `415 Unsupported Media Type` usually means `Content-Type` header is missing or incorrect — use `application/json`.
- If you see `"premium" is not a valid choice.` — update the serializer choices or send one of the allowed values.

### Example: Confirm Payment

- URL: `POST /api/payments/confirm/`
- Body contains `payment_intent_id` and `payment_method_id`.

## Webhook Setup

1. In your Stripe Dashboard, add an endpoint pointing to `https://<your-host>/api/payments/webhook/`.
2. Use the webhook signing secret (from Stripe) in `STRIPE_WEBHOOK_SECRET`.

When testing locally, you can use `stripe-cli` or `ngrok` to expose your server.

## Tests

If tests exist in the repository, run with:

```bash
python manage.py test
```

## Packaging the Project

To create a tarball of the entire project (archive everything in the repo root):

```bash
cd /home/betopia/poritosh/Office_project/Paradise
tar -czf Paradise_project.tar.gz .
```

This will produce `Paradise_project.tar.gz` at the project root.

## Troubleshooting

- Check logs for errors printed by the views (e.g., `print` statements in `payments/views.py`).
- Ensure the authenticated user has the correct permissions for admin-only endpoints.
- If Stripe requests fail, confirm network connectivity and valid API keys.

## Contributing

1. Create a branch for your feature/bugfix.
2. Add tests where applicable.
3. Run migrations and tests.

## Contact / Maintainers

Maintained by the development team in this workspace. For questions about payment flows, check `payments/views.py` and the serializers in `payments/serializers.py`.

---

Generated README on: 2025-12-15

## Detailed Models & Serializer Fields

Below are the important models and serializer fields for the main apps. Use these when writing clients, tests, or extending the API.

**`authentication` app**
- `User` (`authentication.models.User`):
    - `id` (UUID), `email` (string, unique), `name`, `phone_number`, `profile_picture` (URL),
        `stripe_customer_id`, `role` (`user|staff_admin|super_admin`), `subscription_status` (`free|premium|pro`),
        `is_active`, `is_staff`, `is_verified`, `created_at`, `updated_at`.
- Serializers (`authentication/serializers.py`):
    - `RegisterSerializer`: `email`, `password`, `re_type_password`.
    - `LoginSerializer`: `email`, `password`.
    - `UserProfileSerializer`: `user_id`, `name`, `email`, `phone_number`, `role`, `profile_picture`, `is_verified`, `subscription_status`, `created_at`.

**`payments` app**
- `Plan` (`payments.models.Plan`): `id`, `plan_id`, `name`, `price`, `currency`, `billing_cycle`, `stripe_price_id`, plus feature flags/limits like `itineraries_per_month`, `videos_per_month`, `video_price`, `video_quality`, `chatbot_access`, etc.
- `Subscription` (`payments.models.Subscription`): `id`, `user`, `plan`, `stripe_subscription_id`, `status`, `current_period_start`, `current_period_end`, `cancel_at_period_end`, `trial_start`, `trial_end`.
- `Payment` (`payments.models.Payment`): `id`, `user`, `subscription`, `stripe_payment_intent_id`, `payment_type` (`subscription|video_generation|other`), `amount`, `currency`, `status` (`pending|succeeded|failed|refunded`), `payment_method`, `description`, `receipt_url`, `payment_date`.
- Serializers (`payments/serializers.py`):
    - `CreateSubscriptionSerializer`: `plan_type` (choices `premium|pro`), `payment_method_id`.
    - `PaymentSerializer`: `payment_id`, `payment_type`, `amount`, `currency`, `status`, `description`, `receipt_url`, `created_at`.
    - `PlanSerializer`: `plan_id`, `name`, `price`, `currency`, `billing_cycle`, `stripe_price_id`, `features`.

**`user_management` app**
- `UserDeletionRequest` (`user_management.models.UserDeletionRequest`): `id`, `user`, `requested_by`, `deletion_token`, `expires_at`, `is_confirmed`, `is_cancelled`, `created_at`.

## Example Request / Response Bodies

These examples show the expected JSON shapes for key endpoints.

1) Create Payment Intent

Request (POST `/api/payments/create-intent/`)

Headers:
- `Content-Type: application/json`
- `Authorization: Bearer <access_token>`

Body:

```json
{
    "amount": "10.00",
    "currency": "EUR",
    "subscription_plan": "premium"
}
```

Successful Response:

```json
{
    "message": "Payment intent created successfully",
    "data": {
        "client_secret": "<stripe_client_secret>",
        "payment_intent_id": "pi_123...",
        "amount": 10.0,
        "currency": "EUR",
        "publishable_key": "pk_test_..."
    }
}
```

2) Confirm Payment

Request (POST `/api/payments/confirm/`)

Headers:
- `Content-Type: application/json`
- `Authorization: Bearer <access_token>`

Body:

```json
{
    "payment_intent_id": "pi_123...",
    "payment_method_id": "pm_456..."
}
```

Successful Response:

```json
{
    "message": "Payment confirmed successfully",
    "data": {
        "transaction_id": "<uuid>",
        "user_email": "user@example.com",
        "amount": 10.0,
        "currency": "EUR",
        "subscription_status": "premium",
        "payment_date": "2025-12-15T12:34:56Z"
    }
}
```

3) Register (example)

Request (POST `/api/auth/register/`)

```json
{
    "email": "user@example.com",
    "password": "StrongPassw0rd!",
    "re_type_password": "StrongPassw0rd!"
}
```

Successful Response (typical):

```json
{
    "message": "Registration successful",
    "data": {
        "email": "user@example.com",
        "user_id": "<uuid>"
    }
}
```

## API Testing and Postman Collection

I created a basic Postman collection file with the most important endpoints (auth register/login, profile, payments create-intent and confirm). You can import it into Postman to quickly test the API.

- File: `docs/Paradise_Postman_Collection.json`

How to use it:

1. Open Postman → Import → Choose `docs/Paradise_Postman_Collection.json`.
2. Update environment variables in Postman for `base_url` and add an `access_token` variable after login.

## Creating `.env.example`

I added a `.env.example` file at the project root with placeholder values matching the variables listed above. Copy it to `.env` and fill in secrets before running the app.

---


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
