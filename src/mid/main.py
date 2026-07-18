import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import click

from .config import APP_NAME, AppSettings


# Dynamically generates env var name as {APP}_{OPTION} (flat, no command prefix)
def env_opt(*param_decls: str, **kwargs: Any) -> Callable[..., Any]:
    for decl in param_decls:
        if decl.startswith("--"):
            name = decl.lstrip("-").replace("-", "_")
            kwargs.setdefault("envvar", f"{APP_NAME.upper()}_{name.upper()}")
            break
    kwargs.setdefault("show_envvar", True)
    return click.option(*param_decls, **kwargs)


def get_config_path(config_file: Optional[str]) -> Path:
    if config_file:
        return Path(config_file)
    env_var = os.environ.get(f"{APP_NAME.upper()}_CONFIG_FILE")
    if env_var:
        return Path(env_var)
    local = Path(f"{APP_NAME}.json")
    if local.exists():
        return local
    xdg = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / APP_NAME
        / f"{APP_NAME}.json"
    )
    return xdg


@click.group(context_settings=dict(show_default=True))
@env_opt(
    "--config-file",
    type=click.Path(),
    help="Path to config file",
)
@env_opt("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str], verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    config_path = get_config_path(config_file)
    ctx.obj["CONFIG_PATH"] = config_path
    ctx.obj["CONFIG"] = AppSettings.load(config_path)


@cli.group()
def config() -> None:
    """Manage application configuration."""
    pass


@config.command(name="init")
@click.option("--force", is_flag=True, help="Overwrite existing config")
@click.pass_context
def config_init(ctx: click.Context, force: bool) -> None:
    """Create a default config file."""
    path = ctx.obj["CONFIG_PATH"]
    if path.exists() and not force:
        click.echo(f"Config file already exists at {path}. Use --force to overwrite.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    default_settings = _kebab_dict(AppSettings().to_dict())
    path.write_text(json.dumps(default_settings, indent=2))
    click.echo(f"Initialized default config at {path}")


@config.command(name="show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def config_show(ctx: click.Context, as_json: bool) -> None:
    """Display current configuration."""
    cfg = _kebab_dict(ctx.obj["CONFIG"].to_dict())
    if as_json:
        click.echo(json.dumps(cfg, indent=2))
    else:
        for key, value in cfg.items():
            click.echo(f"{key}: {value}")


@config.command(name="path")
@click.pass_context
def config_path_cmd(ctx: click.Context) -> None:
    """Print config file path."""
    click.echo(str(ctx.obj["CONFIG_PATH"]))


@cli.command()
@click.argument("name", required=False)
@env_opt("--admin-token", help="Admin token override")
@click.pass_context
def greet(ctx: click.Context, name: Optional[str], admin_token: Optional[str]) -> None:
    """Print a personalized greeting."""
    cfg = ctx.obj["CONFIG"]
    token = admin_token or cfg.admin_token
    target = name or token or "World"
    click.echo(f"Hello, {target}!")


def _kebab_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        kebab = k.replace("_", "-")
        if isinstance(v, dict):
            v = _kebab_dict(v)
        out[kebab] = v
    return out


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
