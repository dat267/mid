# mid — Opinionated Python CLI Framework

A scalable, opinionated base CLI application in Python — the template I use for every new CLI I build. Modeled after [my Rust CLI template `max`](https://github.com/dat267/max), ported to idiomatic Python with `click` and `pydantic`.

## Install

**Binary** — download from [GitHub Releases](https://github.com/dat267/mid/releases):

**Linux (x86_64):**
```bash
curl -sSfL https://github.com/dat267/mid/releases/latest/download/mid-x86_64-unknown-linux-gnu -o ~/.local/bin/mid
chmod +x ~/.local/bin/mid
```

**macOS (arm64):**
```bash
curl -sSfL https://github.com/dat267/mid/releases/latest/download/mid-aarch64-apple-darwin -o ~/.local/bin/mid
chmod +x ~/.local/bin/mid
```

**Windows (x86_64):**
```powershell
mkdir -Force ~\.local\bin >$null
curl -sSfL https://github.com/dat267/mid/releases/latest/download/mid-x86_64-pc-windows-msvc.exe -o ~\.local\bin\mid.exe
```

**Single-file `.pyz` (requires Python 3.12+):**
```bash
curl -sSfL https://github.com/dat267/mid/releases/latest/download/mid.pyz -o ~/.local/bin/mid.pyz
chmod +x ~/.local/bin/mid.pyz
alias mid=mid.pyz
```

**Via `uv`:**

```bash
uv tool install --from git+https://github.com/dat267/mid mid
```

**Via `pip`:**

```bash
pip install git+https://github.com/dat267/mid
```

**From source:**

```bash
git clone git@github.com:dat267/mid.git
cd mid
uv sync
uv run python -m mid.main greet
```

## Philosophy

Every CLI I write needs the same boilerplate: config file resolution, environment variable overrides, subcommand dispatch, and layered configuration merging. This template bakes all of that in so each new project starts from a solid foundation rather than `main()`.

## Quick Start

**Use as a template:**

Click **"Use this template"** at the top of the [GitHub page](https://github.com/dat267/mid) and clone your new repo, or clone directly:

```bash
git clone git@github.com:dat267/mid.git my-cli
cd my-cli
```

**Clean up template artifacts:**

```bash
# Remove existing tags and release history
git tag | xargs git tag -d
git remote remove origin

# Rename everywhere (replace "mid" with your app name):
#   - pyproject.toml        → project.name
#   - src/mid/config.py     → APP_NAME
#   - src/mid/main.py       → APP_NAME references
#   - README.md             → title, install URLs
#   - .github/workflows     → app references

# Point to your own repository and push
git remote add origin git@github.com:your-user/my-cli.git
git push -u origin main
```

**Build and run:**

```bash
uv run python -m mid.main greet
uv run python -m mid.main config init
uv run python -m mid.main config show
```

## Project Structure

```
src/
  mid/
    __init__.py        # Package marker
    main.py            # Entry point: Click CLI definitions, subcommand dispatch
    config.py          # Config model (Pydantic), JSON loading, env override
tests/
  __init__.py
  test_specificity.py  # Parameter specificity and auto-wiring tests
justfile               # Build, run, test, lint commands
pyproject.toml         # Project metadata, dependencies, tool config
```

## Configuration

### Config File Resolution

The config file is located in this priority order:

1. `--config-file PATH` flag
2. `MID_CONFIG_FILE` environment variable
3. `mid.json` in the current directory
4. `~/.config/mid/mid.json` (XDG config directory)
5. `mid.json` fallback

### File Format (JSON)

```json
{
  "admin-token": null,
  "core": {
    "timeout": "2m",
    "retries": 3
  },
  "debug": false,
  "dry-run": false
}
```

Field naming is `kebab-case` in JSON, which maps to `snake_case` in Python.

### Layered Configuration — Specificity Precedence

Values are resolved with strict override specificity:

```
CLI flags  >  Environment variables  >  Config file  >  Struct defaults
```

Each layer overrides the one before it. A value provided via CLI flag takes ultimate precedence over everything.

### Environment Variable Overrides

Every leaf config field can be overridden with `{APP}_{FLAT_KEY}`:

```bash
# Single fields
MID_ADMIN_TOKEN=bot mid greet
MID_DEBUG=true mid greet

# Nested fields (kebab → underscores, double underscore separator)
MID_CORE__TIMEOUT=30s mid greet
MID_CORE__RETRIES=10 mid greet

# Combined
MID_ADMIN_TOKEN=bot MID_CORE__TIMEOUT=5m mid greet
```

Env-var values are typed automatically: `"true"/"1"/"yes"` → bool, `"42"` → integer, otherwise string.

### Auto-Wiring: Config Values as CLI Flag Defaults

When you add a CLI flag to any subcommand, if the flag's name (in kebab-case) matches a key in the config file, the config value automatically becomes the flag's default via `pydantic`'s field resolution. **No manual wiring required.**

This works through the `AppSettings.load()` method: before a command runs, the config is resolved from file + env vars, and then the command handler checks:

```python
token = admin_token or cfg.admin_token
```

If the CLI flag was not provided, it falls back to the resolved config value.

```python
@cli.command()
@click.argument("name", required=False)
@env_opt("--admin-token", help="Admin token override")
@click.pass_context
def greet(ctx, name, admin_token):
    cfg = ctx.obj["CONFIG"]
    token = admin_token or cfg.admin_token
    target = name or token or "World"
    click.echo(f"Hello, {target}!")
```

#### Field Naming Rules

| Python field | CLI flag | Config key | Auto-wired? |
|---|---|---|---|
| `core.timeout` | `--core-timeout` | `core.timeout` | Yes — matches via flat key `core-timeout` |
| `dry_run` | `--dry-run` | `dry-run` | Yes — atomic kebab key |
| `admin_token` | `--admin-token` | `admin-token` | Yes |
| `url` | N/A | *(none)* | No — no matching config key |

If the field name (after kebab-case conversion) matches a config leaf path, the config value becomes the CLI fallback. Fields with no matching config key are purely local to the subcommand.

### Global Flags

| Flag | Description |
|------|-------------|
| `--config-file` | Path to config file `[env: MID_CONFIG_FILE]` |
| `-v`, `--verbose` | Enable verbose output `[env: MID_VERBOSE]` |

### Built-in Subcommands

#### `config`

Manage the application configuration file.

| Command | Description |
|---------|-------------|
| `config init` | Create a default config file |
| `config init --force` | Overwrite existing config |
| `config show` | Display current configuration |
| `config show --json` | Output as JSON (same as default) |
| `config path` | Print config file path |

#### `greet [name]`

Print a personalized greeting. Supports `--admin-token` which auto-defaults from the config, falls back to `"World"`.

```bash
mid greet                        # Hello, World!
mid greet Alice                  # Hello, Alice!
mid greet --admin-token bot      # Hello, bot!
MID_ADMIN_TOKEN=bot mid greet    # Hello, bot!
MID_ADMIN_TOKEN=env mid greet --admin-token cli  # Hello, cli!  (CLI wins)
```

## Adding a New Subcommand

Adding a subcommand involves two steps:

### 1. Define the Command

In `src/mid/main.py`, add your command using Click decorators:

```python
@cli.command()
@click.option("--core-timeout", help="Request timeout")
@click.option("--retries", type=int, help="Max retries")
@click.argument("url")
@click.pass_context
def fetch(ctx, core_timeout, retries, url):
    """Fetch a resource."""
    cfg = ctx.obj["CONFIG"]

    # Auto-wiring: CLI flag > Config > Default
    timeout = core_timeout or cfg.core.timeout
    max_retries = retries or cfg.core.retries

    click.echo(f"Fetching {url} (timeout={timeout}, retries={max_retries})")
}
```

### 2. Wire It Up

Add the `env_opt` helper if you want env var hints in `--help`, and the handler auto-wires via `cfg` lookup. That's it — config, env vars, and CLI flags are all automatically resolved with the proper precedence.

### Adding Config Fields

If your command needs a new config field, add it to `AppSettings` in `src/mid/config.py`:

```python
class AppSettings(BaseModel):
    admin_token: Optional[str] = None
    debug: bool = False
    dry_run: bool = False
    core: CoreConfig = Field(default_factory=CoreConfig)
    api_key: Optional[str] = None  # New field — auto-wired via MID_API_KEY
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI argument parsing and dispatch |
| `pydantic` | Configuration model, validation, and serialization |
| `pydantic-settings` | Environment variable override resolution |

## Development

```bash
just setup    # Install dev dependencies
just build    # Build single-file mid.pyz with shiv
just test     # Run pytest
just check    # Lint (ruff) + type check (mypy)
just run      # Run mid.pyz
just clean    # Remove build artifacts
```

## License

MIT
