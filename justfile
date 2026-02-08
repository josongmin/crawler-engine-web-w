# Wine Crawler Admin - Just Commands
# Usage: `just <command>` or `just --list`

# ── Admin UI (Frontend) ────────────────────────────────────────────────

# Start admin UI dev server
admin-dev:
    @echo "🚀 Starting admin UI dev server..."
    cd admin-ui && npm run dev

# Build admin UI for production
admin-build:
    @echo "📦 Building admin UI..."
    cd admin-ui && npm run build

# Install admin UI dependencies
admin-install:
    @echo "📥 Installing admin UI dependencies..."
    cd admin-ui && npm install

# Type check admin UI
admin-type:
    @echo "🔍 Type checking admin UI..."
    cd admin-ui && npx tsc --noEmit

# Lint admin UI
admin-lint:
    @echo "✨ Linting admin UI..."
    cd admin-ui && npx eslint src/

# Format admin UI code
admin-format:
    @echo "🎨 Formatting admin UI..."
    cd admin-ui && npx prettier --write "src/**/*.{ts,tsx}"

# ── Backend (Python) ───────────────────────────────────────────────────

# Start backend dev server (FastAPI)
backend-dev:
    @echo "🚀 Starting backend dev server..."
    python -m uvicorn wine_crawler.admin.app:create_app --reload --host 127.0.0.1 --port 8470 --factory

# Install backend dependencies
backend-install:
    @echo "📥 Installing backend dependencies..."
    python -m pip install -U pip
    python -m pip install -e ".[admin,dev]"

# Format backend code
backend-fmt:
    @echo "🎨 Formatting backend..."
    python -m ruff format .

# Lint backend code
backend-lint:
    @echo "✨ Linting backend..."
    python -m ruff check .

# Type check backend (pyright = primary, mypy = secondary)
backend-type:
    @echo "🔍 Type checking backend (pyright)..."
    python -m pyright

# Type check backend with mypy (secondary)
backend-mypy:
    @echo "🔍 Type checking backend (mypy)..."
    python -m mypy .

# Architecture lint (import contracts)
backend-arch:
    @echo "🏗️ Checking architecture contracts..."
    python -m lint-imports 2>/dev/null || lint-imports

# Run backend tests
backend-test:
    @echo "🧪 Running backend tests..."
    python -m pytest

# ── Combined Commands ───────────────────────────────────────────────────

# Install all dependencies (backend + frontend)
install: backend-install admin-install
    @echo "✅ All dependencies installed!"

# Run all checks (backend + frontend)
check: backend-lint backend-type backend-arch backend-test admin-lint admin-type
    @echo "✅ All checks passed!"

# Format all code
format: backend-fmt admin-format
    @echo "✅ All code formatted!"

# Start both dev servers (backend + frontend)
dev: backend-dev admin-dev

# ── Database & Setup ────────────────────────────────────────────────────

# Create virtual environment
venv:
    @echo "🐍 Creating virtual environment..."
    python3 -m venv .venv

# Install Playwright browsers
playwright:
    @echo "🎭 Installing Playwright browsers..."
    python -m playwright install

# Install pre-commit hooks
precommit:
    @echo "🪝 Installing pre-commit hooks..."
    python -m pre_commit install

# ── Utility ────────────────────────────────────────────────────────────

# Show project status
status:
    @echo "📊 Project Status"
    @echo ""
    @echo "Backend:"
    @python --version 2>/dev/null || echo "  ❌ Python not found"
    @echo "Frontend:"
    @cd admin-ui && npm --version 2>/dev/null && echo "  ✅ Node.js $(node --version)" || echo "  ❌ Node.js not found"
    @echo ""
    @echo "Dependencies:"
    @test -d admin-ui/node_modules && echo "  ✅ Frontend deps installed" || echo "  ❌ Frontend deps missing"
    @test -d .venv && echo "  ✅ Python venv exists" || echo "  ❌ Python venv missing"

# Clean build artifacts
clean:
    @echo "🧹 Cleaning build artifacts..."
    rm -rf admin-ui/dist
    rm -rf admin-ui/node_modules/.vite
    rm -rf .venv
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @echo "✅ Cleaned!"

# Default recipe (show help)
default:
    @just --list
