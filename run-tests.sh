#!/bin/bash
# Quick test runner script

echo "========================================="
echo "Multi-Agent Worker API Tests"
echo "========================================="
echo ""

cd backend

echo "📋 Running unit tests..."
echo "-------------------------------------------"
pytest tests/unit/test_worker_service.py -v --tb=short

echo ""
echo "📋 Running integration tests..."
echo "-------------------------------------------"
pytest tests/integration/test_workers_api.py -v --tb=short

echo ""
echo "📊 Test coverage report..."
echo "-------------------------------------------"
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

echo ""
echo "========================================="
echo "✓ Tests completed!"
echo "📊 Coverage report: backend/htmlcov/index.html"
echo "========================================="
