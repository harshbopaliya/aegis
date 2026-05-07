.PHONY: help install dev test lint format security clean docker-build docker-push deploy logs health backup restore docs

help:
	@echo "Aegis - Make Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Install dependencies"
	@echo "  make dev            - Install with development tools"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run all tests with coverage"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make lint           - Run linters (flake8, mypy)"
	@echo "  make format         - Format code (black, isort)"
	@echo "  make security       - Run security checks (bandit, safety)"
	@echo ""
	@echo "Running:"
	@echo "  make run            - Run development server"
	@echo "  make runprod        - Run production server"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-up      - Start Docker Compose stack"
	@echo "  make docker-down    - Stop Docker Compose stack"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy         - Deploy to production"
	@echo "  make health         - Check health endpoints"
	@echo "  make backup         - Trigger backup"
	@echo "  make restore        - Restore from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean temporary files"
	@echo "  make docs           - Build documentation"
	@echo "  make logs           - Show application logs"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=app --cov-report=html --cov-fail-under=80
	@echo "Coverage report: htmlcov/index.html"

test-unit:
	pytest tests/unit/ -v --cov=app --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v

test-security:
	pytest tests/security/ -v

lint:
	flake8 app/
	mypy app/ || true
	isort --check-only app/
	black --check app/

format:
	isort app/
	black app/

security:
	bandit -r app/
	safety check
	pip-audit

clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov .coverage .pytest_cache
	rm -rf .mypy_cache .dmypy.json dmypy.json

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

runprod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

docker-build:
	docker build -t aegis:latest .

docker-push:
	docker tag aegis:latest your-registry/aegis:latest
	docker push your-registry/aegis:latest

docker-up:
	docker-compose up -d
	@echo "Services started. Check with: docker-compose ps"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker system prune -f

health:
	@echo "Checking health endpoints..."
	@curl -s http://localhost:8000/health | jq .
	@curl -s http://localhost:8000/health/ready | jq .
	@curl -s http://localhost:8000/health/live | jq .

deploy:
	@echo "Deploying to production..."
	@docker build -t aegis:prod .
	@docker tag aegis:prod your-registry/aegis:prod
	@docker push your-registry/aegis:prod
	@echo "Image pushed. Update your deployment manifest and apply."

logs:
	tail -f logs/gateway-*.log

backup:
	@echo "Triggering manual backup..."
	@curl -X POST http://localhost:8000/v1/system/backup

restore:
	@echo "Listing available backups:"
	@ls -lh data/backups/
	@echo ""
	@echo "To restore: docker-compose down && mv data/backups/latest.db data/gateway.db && docker-compose up -d"

docs:
	@echo "Documentation is in .md files:"
	@echo "  - README.md (Product overview)"
	@echo "  - API_DOCUMENTATION.md (API reference)"
	@echo "  - DEPLOYMENT.md (Deployment guide)"
	@echo "  - PRODUCTION_TESTING.md (Testing guide)"
	@echo "  - PRODUCTION_README.md (Quick start)"

.DEFAULT_GOAL := help
