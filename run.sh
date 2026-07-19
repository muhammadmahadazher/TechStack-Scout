#!/bin/bash
# Quick start script for TechStack Scout

set -e

echo "🚀 TechStack Scout — Quick Start"
echo "================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo "📦 Starting PostgreSQL and API..."
docker-compose up -d db api

# Wait for DB to be ready
echo "⏳ Waiting for database..."
sleep 5

# Check if already seeded
if docker-compose exec -T db psql -U postgres -d techstack_scout -c "SELECT COUNT(*) FROM domains;" 2>/dev/null | grep -q "0\|ERROR"; then
    echo "🌱 Seeding database with initial domains..."
    docker-compose exec api python seed.py
else
    echo "✅ Database already seeded"
fi

echo ""
echo "✅ TechStack Scout is ready!"
echo ""
echo "🌐 Dashboard: http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "To run the crawler:"
echo "  docker-compose --profile crawler run --rm crawler"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f api"
echo ""
