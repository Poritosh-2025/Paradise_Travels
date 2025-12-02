#!/bin/bash

# Configuration - Update these paths and settings
DJANGO_PROJECT_DIR="/home/betopia/poritosh/Office_project/Paradise"
DJANGO_VENV_PATH="$DJANGO_PROJECT_DIR/venv/bin/activate"
DJANGO_HOST="0.0.0.0"
DJANGO_PORT="9001"



# Function to start a process in a new terminal window
start_in_terminal() {
    gnome-terminal --tab --title="$1" -- bash -c "$2; exec bash"
}

# Start Django server
start_in_terminal "Django Server" \
    "source $DJANGO_VENV_PATH && \
     cd $DJANGO_PROJECT_DIR && \
     python manage.py runserver $DJANGO_HOST:$DJANGO_PORT"



# Start Celery worker
start_in_terminal "Celery Worker" \
    "source $DJANGO_VENV_PATH && \
     cd $DJANGO_PROJECT_DIR && \
     celery -A root worker -l info"

# Start Celery beat (if you need scheduled tasks)
start_in_terminal "Celery Beat" \
    "source $DJANGO_VENV_PATH && \
     cd $DJANGO_PROJECT_DIR && \
     celery -A root beat -l info"

echo "All services started in separate terminal windows"
