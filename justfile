app := "mid"
out := "build"
pyz := out + "/" + app + ".pyz"
bin_dir := out + "/bin"

default: build

# Build a single-file .pyz with all dependencies bundled
build:
    mkdir -p {{out}}
    uv run shiv -o {{pyz}} -p '/usr/bin/env python3' -e {{app}}.main:main .
    rm -rf {{out}}/bdist.* {{out}}/lib

# Build standalone executable with PyInstaller
binary:
    mkdir -p {{bin_dir}}
    uv run pyinstaller --onefile --name {{app}} --paths src src/{{app}}/main.py \
      --distpath {{bin_dir}} --workpath /tmp/{{app}}-pyi-build
    rm -rf /tmp/{{app}}-pyi-build __pycache__/ {{app}}.spec
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
    rm -rf *.spec

# Install dev dependencies
setup:
    uv pip install shiv pyinstaller pytest ruff mypy
