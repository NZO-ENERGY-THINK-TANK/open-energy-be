#!/bin/bash
set -euo pipefail

# Configuration (baked in during instance creation)
# Can be overridden via environment variables
DEFAULT_ECR_REPOSITORY="125975759397.dkr.ecr.il-central-1.amazonaws.com/open-energy-dev"
DEFAULT_DOCKER_IMAGE_TAG="latest"
DEFAULT_SECRET_NAME="open-energy-dev-secrets"
DEFAULT_AWS_REGION="il-central-1"

ECR_REPOSITORY="$DEFAULT_ECR_REPOSITORY"
DOCKER_IMAGE_TAG="$DEFAULT_DOCKER_IMAGE_TAG"
SECRET_NAME="$DEFAULT_SECRET_NAME"
AWS_REGION="$DEFAULT_AWS_REGION"
CONTAINER_NAME="open-energy-app"
CONFIG_DIR="/home/ubuntu/containers/$CONTAINER_NAME"
ENV_FILE="$CONFIG_DIR/.env"

# Allow overrides from environment
if [ -n "${OVERRIDE_ECR_REPOSITORY:-}" ]; then ECR_REPOSITORY="$OVERRIDE_ECR_REPOSITORY"; fi
if [ -n "${OVERRIDE_IMAGE_TAG:-}" ]; then DOCKER_IMAGE_TAG="$OVERRIDE_IMAGE_TAG"; fi
if [ -n "${OVERRIDE_SECRET_NAME:-}" ]; then SECRET_NAME="$OVERRIDE_SECRET_NAME"; fi
if [ -n "${OVERRIDE_AWS_REGION:-}" ]; then AWS_REGION="$OVERRIDE_AWS_REGION"; fi

echo "=========================================="
echo "Open Energy Deployment Script"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Image: $ECR_REPOSITORY:$DOCKER_IMAGE_TAG"
echo "Secret: $SECRET_NAME"
echo "Region: $AWS_REGION"
echo "Config: $CONFIG_DIR"
echo "=========================================="

# Ensure config directory exists
mkdir -p "$CONFIG_DIR"

# Fetch latest secrets
echo "[1/4] Fetching secrets..."
if /usr/local/bin/fetch-secrets.sh "$SECRET_NAME" "$AWS_REGION" "$ENV_FILE"; then
    echo "Secrets updated successfully"
else
    echo "WARNING: Failed to fetch secrets, using existing .env" >&2
fi

# Pull latest image
echo "[2/4] Pulling latest image..."
docker pull "$ECR_REPOSITORY:$DOCKER_IMAGE_TAG"

# Stop and remove existing container
echo "[3/4] Replacing container..."
if docker ps -a --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    docker rm -f "$CONTAINER_NAME" || true
fi

# Start new container
docker run -d     --name "$CONTAINER_NAME"     --restart always     -p 8000:8000     --env-file "$ENV_FILE"     "$ECR_REPOSITORY:$DOCKER_IMAGE_TAG"

# Verify deployment
echo "[4/4] Verifying deployment..."
sleep 5
if docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
    echo "=========================================="
    echo "Deployment successful!"
    CONTAINER_ID=$(docker ps -q --filter name=$CONTAINER_NAME)
    echo "Container ID: $CONTAINER_ID"
    echo "=========================================="
else
    echo "ERROR: Container failed to start" >&2
    docker logs "$CONTAINER_NAME" 2>&1 | tail -50
    exit 1
fi

# Cleanup
docker image prune -f || true