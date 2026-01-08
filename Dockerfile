FROM python:3.13-slim

# Build arguments for flexibility
ARG APP_USER=paradise
ARG APP_UID=1001
ARG APP_GID=1001

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=root.settings
ENV APP_HOME=/app

# Set work directory
WORKDIR ${APP_HOME}

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        git \
        curl \
        postgresql-client \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --shell /bin/bash --create-home ${APP_USER}

# Install Python dependencies
COPY requirements.txt ${APP_HOME}/
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . ${APP_HOME}/

# Copy and set permissions for entrypoint
COPY --chown=${APP_USER}:${APP_USER} docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p ${APP_HOME}/staticfiles ${APP_HOME}/media ${APP_HOME}/logs \
    && chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command (overridden by environment)
CMD ["gunicorn", "root.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "600"]
