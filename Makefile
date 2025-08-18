install-backend:
	chmod +x backend/install.sh
	chmod +x backend/run.sh
	cd backend && ./install.sh

install-frontend:
	chmod +x frontend/install.sh
	chmod +x frontend/run.sh
	cd frontend && ./install.sh

install: install-backend install-frontend

run-backend:
	cd backend && ./run.sh

run-frontend:
	cd frontend && ./run.sh

dev:
	@echo "🚀 Starting development servers..."
	@echo "📡 Backend will run on http://localhost:8000"
	@echo "🌐 Frontend will run on http://localhost:3000"
	@echo "⚡ Press Ctrl+C to stop both servers"
	@echo ""
	@(cd backend && ./run.sh) & (cd frontend && ./run.sh) & wait

help:
	@echo "Available commands:"
	@echo "  make install       - Install both backend and frontend dependencies"
	@echo "  make dev          - Start both development servers"
	@echo "  make run-backend  - Start only backend server"
	@echo "  make run-frontend - Start only frontend server"
	@echo "  make help         - Show this help message"

.PHONY: install install-backend install-frontend run-backend run-frontend dev help

.DEFAULT_GOAL := install
