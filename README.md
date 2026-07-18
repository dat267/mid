# mid CLI Framework

An opinionated Python CLI framework focusing on layered configuration and auto-wiring, inspired by the `max` Rust framework.

## Configuration Precedence
Values are resolved in the following order of priority:
1. **CLI Flags** (Highest)
2. **Environment Variables** (`MID_{KEY}`)
3. **Config File** (`mid.json`)
4. **Defaults** (Lowest)

## Adding a New Subcommand

To add a new command, follow these steps:

### 1. Update the Configuration Model
If your command needs a configurable setting, add it to `AppSettings` in `config.py`.

```python
class AppSettings(BaseSettings):
    # ...
    api_key: Optional[str] = None  # This will be available as --api-key and MID_API_KEY
```

### 2. Create the Command Handler
In `main.py`, define your command and implement the **Auto-Wiring** logic.

```python
@cli.command()
@click.option("--api-key", help="Override API key")
@click.pass_context
def fetch(ctx: click.Context, api_key: Optional[str]) -> None:
    """Fetch data from the API."""
    cfg = ctx.obj["CONFIG"]
    
    # AUTO-WIRING: Priority is CLI Flag -> Config/Env -> Fallback
    final_key = api_key or cfg.api_key or "default_key"
    
    click.echo(f"Fetching with key: {final_key}")
```

## How Auto-Wiring Works

The framework uses `pydantic-settings` to merge environment variables and JSON config files into a single `AppSettings` object. 

1. **Env Vars**: Any variable starting with `MID_` (e.g., `MID_ADMIN_TOKEN`) is automatically mapped to the corresponding field in `AppSettings`.
2. **Config File**: The `AppSettings.load()` method searches for `mid.json` in the current directory or `~/.config/mid/mid.json` and merges it.
3. **CLI Injection**: By using `api_key or cfg.api_key`, the command handler explicitly implements the precedence chain, ensuring that an explicit CLI flag always overrides the stored configuration.

## Development

### Installation
```bash
uv pip install -r pyproject.toml # if dependencies are listed
```

### Linting & Types
```bash
ruff check .
mypy .
```
