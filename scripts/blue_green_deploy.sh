#!/bin/bash

# Blue-Green Deployment Script for KDP Strategist
# This script handles blue-green deployments using Docker Compose

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.blue-green.yml"
ENV_FILE="$PROJECT_ROOT/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required files exist
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Creating default .env file..."
        cat > "$ENV_FILE" << EOF
# Database Configuration
DATABASE_URL=postgresql://kdp_user:kdp_pass@postgres:5432/kdp_strategist
DB_USER=kdp_user
DB_PASSWORD=kdp_pass

# Cache Configuration
CACHE_URL=redis://redis:6379/0

# Monitoring
GRAFANA_PASSWORD=admin123

# Slack Notifications (optional)
SLACK_WEBHOOK_URL=

# Feature Flags
FEATURE_FLAGS_ENABLED=true
EOF
    fi
    
    # Check if Docker and Docker Compose are available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Get current active environment (blue or green)
get_active_environment() {
    local blue_running=$(docker-compose -f "$COMPOSE_FILE" ps -q kdp-strategist-blue 2>/dev/null)
    local green_running=$(docker-compose -f "$COMPOSE_FILE" ps -q kdp-strategist-green 2>/dev/null)
    
    if [[ -n "$blue_running" ]] && [[ -z "$green_running" ]]; then
        echo "blue"
    elif [[ -z "$blue_running" ]] && [[ -n "$green_running" ]]; then
        echo "green"
    elif [[ -n "$blue_running" ]] && [[ -n "$green_running" ]]; then
        echo "both"
    else
        echo "none"
    fi
}

# Get inactive environment
get_inactive_environment() {
    local active=$(get_active_environment)
    case $active in
        "blue") echo "green" ;;
        "green") echo "blue" ;;
        "both") echo "unknown" ;;
        "none") echo "blue" ;;  # Default to blue if nothing is running
    esac
}

# Health check function
health_check() {
    local environment=$1
    local max_attempts=${2:-10}
    local attempt=1
    
    log_info "Performing health check for $environment environment..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T "kdp-strategist-$environment" curl -f http://localhost:8000/api/health &>/dev/null; then
            log_success "$environment environment is healthy"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$environment environment failed health check after $max_attempts attempts"
    return 1
}

# Deploy to inactive environment
deploy_to_inactive() {
    local version=${1:-$(date +%Y%m%d_%H%M%S)}
    local active_env=$(get_active_environment)
    local inactive_env=$(get_inactive_environment)
    
    log_info "Current active environment: $active_env"
    log_info "Deploying version $version to $inactive_env environment..."
    
    # Create backup
    log_info "Creating backup..."
    python "$SCRIPT_DIR/deploy.py" backup production --version "$version"
    
    # Build and start inactive environment
    log_info "Building and starting $inactive_env environment..."
    docker-compose -f "$COMPOSE_FILE" --profile green-deployment build "kdp-strategist-$inactive_env"
    docker-compose -f "$COMPOSE_FILE" --profile green-deployment up -d "kdp-strategist-$inactive_env"
    
    # Wait for container to be ready
    log_info "Waiting for $inactive_env environment to be ready..."
    sleep 30
    
    # Perform health check
    if ! health_check "$inactive_env"; then
        log_error "Health check failed for $inactive_env environment"
        log_info "Stopping $inactive_env environment..."
        docker-compose -f "$COMPOSE_FILE" stop "kdp-strategist-$inactive_env"
        return 1
    fi
    
    # Run smoke tests
    log_info "Running smoke tests on $inactive_env environment..."
    if ! docker-compose -f "$COMPOSE_FILE" exec -T "kdp-strategist-$inactive_env" python -c "
import sys
sys.path.append('src/kdp_strategist/data')
from feature_flags import FeatureFlagManager
manager = FeatureFlagManager()
status = manager.get_flag_status()
assert status is not None
print('Smoke tests passed')
"; then
        log_error "Smoke tests failed for $inactive_env environment"
        return 1
    fi
    
    log_success "Deployment to $inactive_env environment completed successfully"
    return 0
}

# Switch traffic from active to inactive environment
switch_traffic() {
    local active_env=$(get_active_environment)
    local inactive_env=$(get_inactive_environment)
    
    if [[ "$active_env" == "both" ]]; then
        log_error "Both environments are running. Cannot determine which to switch from."
        return 1
    fi
    
    if [[ "$active_env" == "none" ]]; then
        log_error "No environments are running. Cannot switch traffic."
        return 1
    fi
    
    log_info "Switching traffic from $active_env to $inactive_env..."
    
    # Update Traefik labels to switch traffic
    # Disable old environment
    docker-compose -f "$COMPOSE_FILE" exec traefik \
        docker update --label-add "traefik.enable=false" "kdp-strategist-$active_env" || true
    
    # Enable new environment
    docker-compose -f "$COMPOSE_FILE" exec traefik \
        docker update --label-add "traefik.enable=true" "kdp-strategist-$inactive_env" || true
    
    # Wait for traffic switch to take effect
    log_info "Waiting for traffic switch to take effect..."
    sleep 30
    
    # Verify new environment is receiving traffic
    log_info "Verifying traffic switch..."
    if health_check "$inactive_env" 3; then
        log_success "Traffic successfully switched to $inactive_env environment"
        
        # Stop old environment after successful switch
        log_info "Stopping old $active_env environment..."
        docker-compose -f "$COMPOSE_FILE" stop "kdp-strategist-$active_env"
        
        return 0
    else
        log_error "Traffic switch verification failed"
        
        # Rollback traffic switch
        log_warning "Rolling back traffic switch..."
        docker-compose -f "$COMPOSE_FILE" exec traefik \
            docker update --label-add "traefik.enable=true" "kdp-strategist-$active_env" || true
        docker-compose -f "$COMPOSE_FILE" exec traefik \
            docker update --label-add "traefik.enable=false" "kdp-strategist-$inactive_env" || true
        
        return 1
    fi
}

# Full blue-green deployment
full_deploy() {
    local version=${1:-$(date +%Y%m%d_%H%M%S)}
    
    log_info "Starting full blue-green deployment (version: $version)..."
    
    # Deploy to inactive environment
    if ! deploy_to_inactive "$version"; then
        log_error "Deployment to inactive environment failed"
        return 1
    fi
    
    # Switch traffic
    if ! switch_traffic; then
        log_error "Traffic switch failed"
        return 1
    fi
    
    log_success "Blue-green deployment completed successfully!"
    return 0
}

# Rollback to previous environment
rollback() {
    local active_env=$(get_active_environment)
    local inactive_env=$(get_inactive_environment)
    
    log_warning "Starting rollback from $active_env to $inactive_env..."
    
    # Check if inactive environment is available
    if ! docker-compose -f "$COMPOSE_FILE" ps "kdp-strategist-$inactive_env" &>/dev/null; then
        log_error "Inactive environment ($inactive_env) is not available for rollback"
        return 1
    fi
    
    # Start inactive environment if not running
    log_info "Starting $inactive_env environment..."
    docker-compose -f "$COMPOSE_FILE" up -d "kdp-strategist-$inactive_env"
    
    # Health check on inactive environment
    if ! health_check "$inactive_env"; then
        log_error "Rollback failed: $inactive_env environment is not healthy"
        return 1
    fi
    
    # Switch traffic back
    if switch_traffic; then
        log_success "Rollback completed successfully"
        
        # Update feature flags to safe state
        log_info "Setting feature flags to safe state..."
        python "$SCRIPT_DIR/manage_feature_flags.py" set-percentage 0
        
        return 0
    else
        log_error "Rollback failed during traffic switch"
        return 1
    fi
}

# Emergency rollback (disable Simple Trends)
emergency_rollback() {
    log_warning "EMERGENCY ROLLBACK: Disabling Simple Trends system..."
    
    # Set feature flags to emergency state
    python "$SCRIPT_DIR/manage_feature_flags.py" set-percentage 0
    python "$SCRIPT_DIR/manage_feature_flags.py" disable-ab-test
    python "$SCRIPT_DIR/manage_feature_flags.py" unforce-simple-trends
    
    log_success "Emergency rollback completed - all traffic routed to Google Trends"
}

# Show deployment status
show_status() {
    local active_env=$(get_active_environment)
    
    echo "=== Deployment Status ==="
    echo "Active Environment: $active_env"
    echo
    
    echo "=== Container Status ==="
    docker-compose -f "$COMPOSE_FILE" ps
    echo
    
    echo "=== Feature Flag Status ==="
    python "$SCRIPT_DIR/manage_feature_flags.py" status
    echo
    
    echo "=== Health Checks ==="
    for env in blue green; do
        if docker-compose -f "$COMPOSE_FILE" ps -q "kdp-strategist-$env" &>/dev/null; then
            if health_check "$env" 1; then
                echo "$env: HEALTHY"
            else
                echo "$env: UNHEALTHY"
            fi
        else
            echo "$env: NOT RUNNING"
        fi
    done
}

# Main function
main() {
    local command=${1:-help}
    local version=$2
    
    case $command in
        "deploy")
            check_prerequisites
            full_deploy "$version"
            ;;
        "deploy-only")
            check_prerequisites
            deploy_to_inactive "$version"
            ;;
        "switch")
            check_prerequisites
            switch_traffic
            ;;
        "rollback")
            check_prerequisites
            rollback
            ;;
        "emergency")
            emergency_rollback
            ;;
        "status")
            show_status
            ;;
        "help"|*)
            echo "Usage: $0 {deploy|deploy-only|switch|rollback|emergency|status} [version]"
            echo
            echo "Commands:"
            echo "  deploy [version]    - Full blue-green deployment"
            echo "  deploy-only [version] - Deploy to inactive environment only"
            echo "  switch              - Switch traffic to inactive environment"
            echo "  rollback            - Rollback to previous environment"
            echo "  emergency           - Emergency rollback (disable Simple Trends)"
            echo "  status              - Show deployment status"
            echo "  help                - Show this help message"
            echo
            echo "Examples:"
            echo "  $0 deploy v1.2.3"
            echo "  $0 rollback"
            echo "  $0 status"
            ;;
    esac
}

# Run main function with all arguments
main "$@"