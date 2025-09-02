#!/bin/bash

# MCP Research File Server - Docker Setup Script

set -e

echo "🚀 Setting up Qdrant for MCP Research File Server..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Start Qdrant using docker-compose
echo "📦 Starting Qdrant vector database..."
docker-compose -f docker/docker-compose.yml up -d

# Wait for Qdrant to be healthy
echo "⏳ Waiting for Qdrant to be ready..."
timeout 60s bash -c 'until curl -f http://localhost:6333/health > /dev/null 2>&1; do sleep 2; done'

if [ $? -eq 0 ]; then
    echo "✅ Qdrant is running and healthy!"
    echo "🌐 Qdrant REST API: http://localhost:6333"
    echo "📊 Qdrant Web UI: http://localhost:6333/dashboard"
else
    echo "❌ Qdrant failed to start or is not healthy"
    echo "🔍 Check logs with: docker-compose -f docker/docker-compose.yml logs"
    exit 1
fi

echo ""
echo "🎉 Docker setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Run 'pnpm install' to install dependencies"
echo "3. Run 'pnpm dev' to start the development server"