app := "mid"
out := "build"
pyz := out + "/" + app + ".pyz"

default: build

# Build a single-file .pyz with all dependencies bundled
build:
    mkdir -p {{out}}
    uv run shiv -o {{pyz}} -p '/usr/bin/env python3' -e {{app}}.main:main .
    rm -rf {{out}}/bdist.* {{out}}/lib

# Run the .pyz
run *args:
    python {{pyz}} {{args}}

# Run tests
test:
    uv run pytest

# Lint and type check
check:
    uv run ruff check .
    uv run mypy .

# Clean generated files
clean:
    rm -rf {{out}}/ __pycache__/ .mypy_cache/ .pytest_cache/ .ruff_cache/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Install dev dependencies
setup:
    uv pip install shiv pytest ruff mypy
