#!/bin/bash

# ===========================================
# PARADISE - Unified Docker Management Script
# ===========================================
# Single script for all environments
# Usage: ./dev.sh [command] [options]
# ===========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ===========================================
# Helper Functions
# ===========================================

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     ${MAGENTA}PARADISE${CYAN} - Docker Management          ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}▶${NC} $1"
}

print_error() {
    echo -e "${RED}✖ ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✔${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ===========================================
# Pre-flight Checks
# ===========================================

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        echo "Install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running!"
        echo ""
        echo "Try one of these:"
        echo "  sudo systemctl start docker"
        echo "  sudo service docker start"
        exit 1
    fi
}

check_docker_compose() {
    if ! docker compose version &> /dev/null; then
        if ! docker-compose version &> /dev/null; then
            print_error "Docker Compose is not installed!"
            exit 1
        fi
        # Use legacy docker-compose
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
}

check_env_file() {
    if [ ! -f ".env" ]; then
        print_error "Environment file .env not found!"
        echo ""
        echo "Create one by copying an example:"
        echo "  cp .env.example .env        # For local development"
        echo "  cp .env.staging .env        # For staging"
        echo "  cp .env.production .env     # For production"
        echo ""
        exit 1
    fi
    
    # Load environment for display
    source .env 2>/dev/null || true
    print_info "Environment: ${ENVIRONMENT:-local}"
}

# ===========================================
# Docker Permission Fix
# ===========================================

fix_permissions() {
    print_header
    print_status "Fixing Docker permissions..."
    
    # Check if user is already in docker group
    if groups | grep -q docker; then
        print_success "User already in docker group"
    else
        print_status "Adding $USER to docker group..."
        sudo usermod -aG docker $USER
        print_success "Added $USER to docker group"
        print_warning "You need to log out and log back in for changes to take effect"
        print_info "Or run: newgrp docker"
    fi
    
    # Ensure AppArmor is running (prevents permission issues)
    if command -v aa-status &> /dev/null; then
        print_status "Ensuring AppArmor is enabled..."
        sudo systemctl enable apparmor 2>/dev/null || true
        sudo systemctl start apparmor 2>/dev/null || true
        print_success "AppArmor enabled"
    fi
    
    # Restart Docker to apply changes
    print_status "Restarting Docker..."
    sudo systemctl restart docker
    sleep 3
    
    print_success "Docker permissions configured!"
    echo ""
    print_info "Next steps:"
    echo "  1. Log out and log back in (or run: newgrp docker)"
    echo "  2. Run: ./dev.sh start"
}

# ===========================================
# Cleanup Functions
# ===========================================

cleanup() {
    print_header
    print_status "Cleaning up Docker environment..."
    
    # Stop project containers
    print_status "Stopping containers..."
    $COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    
    # Stop any leftover containers with 'paradise' in name
    print_status "Removing stale containers..."
    docker ps -aq --filter "name=paradise" | xargs -r docker rm -f 2>/dev/null || true
    
    # Remove project networks
    print_status "Removing networks..."
    docker network ls --filter "name=paradise" -q | xargs -r docker network rm 2>/dev/null || true
    
    # Prune
    print_status "Pruning unused resources..."
    docker system prune -f
    
    print_success "Cleanup complete!"
}

deep_clean() {
    print_header
    print_warning "This will remove ALL Paradise Docker data including:"
    echo "  • All containers"
    echo "  • All images"
    echo "  • All volumes (DATABASE DATA WILL BE LOST!)"
    echo "  • All networks"
    echo ""
    read -p "Are you sure? Type 'yes' to confirm: " -r
    echo
    
    if [[ $REPLY == "yes" ]]; then
        cleanup
        
        print_status "Removing volumes..."
        docker volume ls --filter "name=paradise" -q | xargs -r docker volume rm 2>/dev/null || true
        
        print_status "Removing images..."
        docker images --filter "reference=paradise*" -q | xargs -r docker rmi -f 2>/dev/null || true
        
        print_status "Final prune..."
        docker system prune -af --volumes
        
        print_success "Deep clean complete!"
    else
        print_info "Cancelled"
    fi
}

# ===========================================
# Service Management
# ===========================================

start() {
    print_header
    check_env_file
    
    print_status "Building and starting services..."
    $COMPOSE_CMD up -d --build
    
    echo ""
    print_success "Services started!"
    echo ""
    
    # Get ports from env
    source .env 2>/dev/null || true
    WEB_PORT="${WEB_EXTERNAL_PORT:-12001}"
    DB_PORT="${DB_EXTERNAL_PORT:-12011}"
    REDIS_PORT="${REDIS_EXTERNAL_PORT:-12021}"
    
    echo -e "${BLUE}Access Points:${NC}"
    echo -e "  • API:     http://localhost:${WEB_PORT}"
    echo -e "  • DB:      localhost:${DB_PORT}"
    echo -e "  • Redis:   localhost:${REDIS_PORT}"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  • View logs:    ./dev.sh logs"
    echo -e "  • Check status: ./dev.sh status"
    echo -e "  • Stop:         ./dev.sh stop"
}

stop() {
    print_header
    print_status "Stopping services..."
    $COMPOSE_CMD down
    print_success "Services stopped!"
}

restart() {
    print_header
    print_status "Restarting services..."
    $COMPOSE_CMD down
    $COMPOSE_CMD up -d --build
    print_success "Services restarted!"
}

logs() {
    SERVICE="${2:-}"
    if [ -n "$SERVICE" ]; then
        print_info "Showing logs for $SERVICE (Ctrl+C to exit)..."
        $COMPOSE_CMD logs -f "$SERVICE"
    else
        print_info "Showing all logs (Ctrl+C to exit)..."
        $COMPOSE_CMD logs -f
    fi
}

status() {
    print_header
    check_env_file
    
    echo -e "${BLUE}Service Status:${NC}"
    echo ""
    $COMPOSE_CMD ps
    echo ""
    
    # Health check
    echo -e "${BLUE}Health Checks:${NC}"
    
    # Check web
    source .env 2>/dev/null || true
    WEB_PORT="${WEB_EXTERNAL_PORT:-12001}"
    
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${WEB_PORT}/admin/" | grep -q "200\|301\|302"; then
        echo -e "  • Web:   ${GREEN}✔ Healthy${NC}"
    else
        echo -e "  • Web:   ${RED}✖ Not responding${NC}"
    fi
    
    # Check DB
    if $COMPOSE_CMD exec -T db pg_isready -U paradise_user -d paradise_db &>/dev/null; then
        echo -e "  • DB:    ${GREEN}✔ Healthy${NC}"
    else
        echo -e "  • DB:    ${RED}✖ Not responding${NC}"
    fi
    
    # Check Redis
    if $COMPOSE_CMD exec -T redis redis-cli ping &>/dev/null; then
        echo -e "  • Redis: ${GREEN}✔ Healthy${NC}"
    else
        echo -e "  • Redis: ${RED}✖ Not responding${NC}"
    fi
}

build() {
    print_header
    check_env_file
    print_status "Building images..."
    $COMPOSE_CMD build
    print_success "Build complete!"
}

# ===========================================
# Django Management
# ===========================================

manage() {
    shift
    print_status "Running: python manage.py $@"
    $COMPOSE_CMD exec web python manage.py "$@"
}

shell() {
    print_status "Opening Django shell..."
    $COMPOSE_CMD exec web python manage.py shell
}

bash_shell() {
    SERVICE="${2:-web}"
    print_status "Opening bash in $SERVICE..."
    $COMPOSE_CMD exec "$SERVICE" bash
}

# ===========================================
# Database Operations
# ===========================================

db_shell() {
    print_status "Opening PostgreSQL shell..."
    $COMPOSE_CMD exec db psql -U paradise_user -d paradise_db
}

db_backup() {
    print_header
    mkdir -p backups
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    source .env 2>/dev/null || true
    BACKUP_FILE="backups/paradise_${ENVIRONMENT:-local}_${TIMESTAMP}.sql"
    
    print_status "Creating backup: $BACKUP_FILE"
    $COMPOSE_CMD exec -T db pg_dump -U paradise_user paradise_db > "$BACKUP_FILE"
    
    # Compress
    gzip "$BACKUP_FILE"
    print_success "Backup created: ${BACKUP_FILE}.gz"
    
    # Show recent backups
    echo ""
    echo -e "${BLUE}Recent backups:${NC}"
    ls -lh backups/*.gz 2>/dev/null | tail -5
}

db_restore() {
    BACKUP_FILE="${2:-}"
    
    if [ -z "$BACKUP_FILE" ]; then
        print_error "Please specify a backup file"
        echo ""
        echo "Usage: ./dev.sh db:restore <backup_file>"
        echo ""
        echo "Available backups:"
        ls -lh backups/*.gz 2>/dev/null || echo "  No backups found"
        exit 1
    fi
    
    print_header
    print_warning "This will REPLACE the current database!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Restoring from: $BACKUP_FILE"
        
        # Decompress if needed
        if [[ "$BACKUP_FILE" == *.gz ]]; then
            gunzip -c "$BACKUP_FILE" | $COMPOSE_CMD exec -T db psql -U paradise_user -d paradise_db
        else
            cat "$BACKUP_FILE" | $COMPOSE_CMD exec -T db psql -U paradise_user -d paradise_db
        fi
        
        print_success "Database restored!"
    else
        print_info "Cancelled"
    fi
}

db_reset() {
    print_header
    print_warning "This will DELETE ALL DATABASE DATA!"
    read -p "Type 'reset' to confirm: " -r
    echo
    
    if [[ $REPLY == "reset" ]]; then
        print_status "Resetting database..."
        
        $COMPOSE_CMD down -v
        
        source .env 2>/dev/null || true
        docker volume rm "paradise_postgres_${ENVIRONMENT:-local}" 2>/dev/null || true
        
        print_status "Restarting services..."
        $COMPOSE_CMD up -d --build
        
        print_success "Database reset complete!"
    else
        print_info "Cancelled"
    fi
}

# ===========================================
# Environment Setup
# ===========================================

setup_env() {
    ENV_TYPE="${2:-local}"
    print_header
    
    case "$ENV_TYPE" in
        local|dev)
            print_status "Setting up LOCAL environment..."
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_info "Edit .env with your settings, then run: ./dev.sh start"
            ;;
        staging)
            print_status "Setting up STAGING environment..."
            cp .env.staging .env
            print_success "Created .env from .env.staging"
            print_warning "Update sensitive values in .env before starting!"
            ;;
        prod|production)
            print_status "Setting up PRODUCTION environment..."
            cp .env.production .env
            print_success "Created .env from .env.production"
            print_warning "UPDATE ALL SENSITIVE VALUES in .env before starting!"
            print_warning "Never use default passwords in production!"
            ;;
        *)
            print_error "Unknown environment: $ENV_TYPE"
            echo "Available: local, staging, production"
            exit 1
            ;;
    esac
}

# ===========================================
# Quick Health Check
# ===========================================

health() {
    print_header
    check_env_file
    
    source .env 2>/dev/null || true
    WEB_PORT="${WEB_EXTERNAL_PORT:-12001}"
    
    echo -e "${BLUE}Running health checks...${NC}"
    echo ""
    
    # Docker
    if docker info &>/dev/null; then
        echo -e "Docker:     ${GREEN}✔ Running${NC}"
    else
        echo -e "Docker:     ${RED}✖ Not running${NC}"
    fi
    
    # Containers
    RUNNING=$($COMPOSE_CMD ps --filter "status=running" -q 2>/dev/null | wc -l)
    TOTAL=$($COMPOSE_CMD ps -q 2>/dev/null | wc -l)
    if [ "$RUNNING" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        echo -e "Containers: ${GREEN}✔ $RUNNING/$TOTAL running${NC}"
    else
        echo -e "Containers: ${YELLOW}⚠ $RUNNING/$TOTAL running${NC}"
    fi
    
    # API endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${WEB_PORT}/admin/" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        echo -e "API:        ${GREEN}✔ Responding (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "API:        ${RED}✖ Not responding (HTTP $HTTP_CODE)${NC}"
    fi
}

# ===========================================
# Help
# ===========================================

show_help() {
    print_header
    echo -e "${BLUE}Usage:${NC} ./dev.sh [command] [options]"
    echo ""
    echo -e "${CYAN}━━━ Environment Setup ━━━${NC}"
    echo "  setup [env]        Create .env file (local/staging/production)"
    echo "  fix-permissions    Fix Docker permissions (run once)"
    echo ""
    echo -e "${CYAN}━━━ Service Management ━━━${NC}"
    echo "  start              Build and start all services"
    echo "  stop               Stop all services"
    echo "  restart            Rebuild and restart all services"
    echo "  status             Show service status and health"
    echo "  health             Quick health check"
    echo "  logs [service]     View logs (all or specific service)"
    echo "  build              Build images without starting"
    echo ""
    echo -e "${CYAN}━━━ Django Commands ━━━${NC}"
    echo "  manage [cmd]       Run Django management command"
    echo "  shell              Open Django shell"
    echo "  bash [service]     Open bash in container (default: web)"
    echo ""
    echo -e "${CYAN}━━━ Database ━━━${NC}"
    echo "  db:shell           Open PostgreSQL shell"
    echo "  db:backup          Create database backup"
    echo "  db:restore [file]  Restore from backup"
    echo "  db:reset           Reset database (DELETES ALL DATA)"
    echo ""
    echo -e "${CYAN}━━━ Maintenance ━━━${NC}"
    echo "  cleanup            Clean up Docker resources"
    echo "  deep-clean         Remove everything including volumes"
    echo ""
    echo -e "${CYAN}━━━ Examples ━━━${NC}"
    echo "  ./dev.sh setup local           # Setup local environment"
    echo "  ./dev.sh start                 # Start services"
    echo "  ./dev.sh logs web              # View web logs"
    echo "  ./dev.sh manage migrate        # Run migrations"
    echo "  ./dev.sh db:backup             # Backup database"
    echo ""
}

# ===========================================
# Main
# ===========================================

# Run pre-flight checks
check_docker
check_docker_compose

# Command handler
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    build)
        build
        ;;
    logs)
        logs "$@"
        ;;
    status)
        status
        ;;
    health)
        health
        ;;
    manage)
        manage "$@"
        ;;
    shell)
        shell
        ;;
    bash)
        bash_shell "$@"
        ;;
    db:shell)
        db_shell
        ;;
    db:backup)
        db_backup
        ;;
    db:restore)
        db_restore "$@"
        ;;
    db:reset)
        db_reset
        ;;
    setup)
        setup_env "$@"
        ;;
    cleanup)
        cleanup
        ;;
    deep-clean)
        deep_clean
        ;;
    fix-permissions)
        fix_permissions
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac