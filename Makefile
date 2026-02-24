.PHONY: help install install-dev test test-unit test-integration lint format clean dev-setup run-cli run-test run-api build ui-install ui-dev ui-build setup-db benchmark

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Sena Development Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# ============================================
# Installation
# ============================================

install: ## Install production dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# ============================================
# Testing
# ============================================

test: ## Run all tests
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	pytest tests/integration/ -v -m integration

test-fast: ## Run tests without slow markers
	pytest tests/ -v -m "not slow"

# ============================================
# Code Quality
# ============================================

lint: ## Run all linters
	@echo "$(BLUE)Running Ruff...$(RESET)"
	ruff check src/ tests/
	@echo "$(BLUE)Running Black check...$(RESET)"
	black --check src/ tests/
	@echo "$(BLUE)Running MyPy...$(RESET)"
	mypy src/ --ignore-missing-imports
	@echo "$(GREEN)All linters passed!$(RESET)"

format: ## Format code with Black and Ruff
	@echo "$(BLUE)Running Ruff fix...$(RESET)"
	ruff check --fix src/ tests/
	@echo "$(BLUE)Running Black...$(RESET)"
	black src/ tests/
	@echo "$(GREEN)Code formatted!$(RESET)"

typecheck: ## Run type checking with MyPy
	mypy src/ --ignore-missing-imports

# ============================================
# Development
# ============================================

dev-setup: ## Complete development environment setup
	@echo "$(BLUE)Creating virtual environment...$(RESET)"
	python -m venv venv
	@echo "$(YELLOW)Virtual environment created. Activate with:$(RESET)"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Linux/Mac: source venv/bin/activate"
	@echo "$(YELLOW)Then run: make install-dev$(RESET)"

setup-db: ## Initialize the database
	python scripts/setup_database.py

run-cli: ## Run Sena in CLI mode
	python -m src.main --cli

run-test: ## Run Sena in test mode (with debug UI)
	python -m src.main --test

run-api: ## Run API server only
	uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000

bootstrap: ## Run bootstrapper checks
	python -m src.main --bootstrap

benchmark: ## Run performance benchmarks
	python scripts/benchmark.py

# ============================================
# UI Development
# ============================================

ui-install: ## Install UI dependencies
	cd src/ui/behind-the-sena && npm install
	cd src/ui/sena-app && npm install

ui-dev: ## Run Behind-The-Sena in development mode
	cd src/ui/behind-the-sena && npm run dev

ui-build: ## Build UI applications
	cd src/ui/behind-the-sena && npm run build
	cd src/ui/sena-app && npm run build

# ============================================
# Build & Distribution
# ============================================

build: ## Build executable
	pyinstaller --name=Sena \
		--onefile \
		--windowed \
		--icon=assets/icons/icon.ico \
		--add-data "src/config:config" \
		--add-data "src/extensions/core:extensions/core" \
		src/main.py

build-clean: clean build ## Clean build then rebuild

# ============================================
# Cleanup
# ============================================

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(RESET)"

clean-logs: ## Clean log files
	rm -rf data/logs/*.log*
	rm -rf data/logs/sessions/*.log

clean-data: ## Clean all runtime data (CAUTION: deletes database!)
	rm -rf data/memory/sena.db*
	rm -rf data/memory/chroma/
	rm -rf data/benchmarks/results.json
	rm -rf data/extensions/generated/*

clean-all: clean clean-logs ## Clean everything except data
	@echo "$(YELLOW)Note: Use 'make clean-data' to also clean database$(RESET)"

# ============================================
# Docker (optional)
# ============================================

docker-build: ## Build Docker image
	docker build -t sena:latest .

docker-run: ## Run Sena in Docker
	docker run -p 8000:8000 -v $(PWD)/data:/app/data sena:latest

# ============================================
# Ollama Models
# ============================================

install-models: ## Install required Ollama models
ifeq ($(OS),Windows_NT)
	scripts\\install_models.bat
else
	bash scripts/install_models.sh
endif

check-models: ## Check if required models are installed
	@echo "$(BLUE)Checking Ollama models...$(RESET)"
	@ollama list