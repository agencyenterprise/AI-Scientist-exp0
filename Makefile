lint:
	@echo "🔍 Linting"
	@echo "🎨 Auto-formatting"
	uv run black .
	uv run isort .
	uvx flake8 .
	uv run mypy .
	uv run python3 check_inline_imports.py