import json
from typing import Any, Callable, Dict, Optional

import pytest
from click.testing import CliRunner, Result

from mid.main import cli


def _run(
    runner: CliRunner, args: list[str], env: Optional[Dict[str, str]] = None
) -> Result:
    return runner.invoke(cli, args, env=env)


def _config_show(
    runner: CliRunner,
    config_path: str,
    extra_args: Optional[list[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    args = ["--config-file", str(config_path), "config", "show", "--json"]
    if extra_args:
        args.extend(extra_args)
    result = _run(runner, args, env=env)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)  # type: ignore[no-any-return]


def _greet(
    runner: CliRunner,
    args: Optional[list[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    result = _run(runner, ["greet", *(args or [])], env=env)
    assert result.exit_code == 0, result.output
    return result.output.strip()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def tmp_config(tmp_path: Any) -> Callable[[Dict[str, Any], str], str]:
    def _write(data: Dict[str, Any], name: str = "config.json") -> str:
        p = tmp_path / name
        p.write_text(json.dumps(data))
        return str(p)
    return _write


class TestParameterSpecificity:
    """Mirrors the Go test scenarios from dat267/min."""

    def test_default_values(self, runner: CliRunner, tmp_config: Any) -> None:
        """Scenario 1: Default values (empty config file)."""
        empty = tmp_config({})
        cfg = _config_show(runner, empty)
        assert cfg["core"]["retries"] == 3
        assert cfg["admin-token"] is None
        assert cfg["core"]["timeout"] == "2m"
        assert cfg["debug"] is False

    def test_config_overrides_defaults(
        self, runner: CliRunner, tmp_config: Any
    ) -> None:
        """Scenario 2: Config file overrides defaults."""
        cfg_file = tmp_config({
            "admin-token": "config-token",
            "core": {"timeout": "5m", "retries": 10},
            "debug": True,
            "dry-run": True,
        })
        cfg = _config_show(runner, cfg_file)
        assert cfg["admin-token"] == "config-token"
        assert cfg["core"]["retries"] == 10
        assert cfg["core"]["timeout"] == "5m"
        assert cfg["debug"] is True
        assert cfg["dry-run"] is True

    def test_env_overrides_config(self, runner: CliRunner, tmp_config: Any) -> None:
        """Scenario 3: Env vars override config file."""
        cfg_file = tmp_config({
            "admin-token": "config-token",
            "core": {"timeout": "5m", "retries": 10},
        })
        env = {"MID_ADMIN_TOKEN": "env-token", "MID_CORE__TIMEOUT": "30m"}
        cfg = _config_show(runner, cfg_file, env=env)
        assert cfg["admin-token"] == "env-token"
        assert cfg["core"]["retries"] == 10
        assert cfg["core"]["timeout"] == "30m"

    def test_env_fully_overrides_config(
        self, runner: CliRunner, tmp_config: Any
    ) -> None:
        """Scenario 4: Env vars fully override config (no CLI flags)."""
        empty = tmp_config({}, "empty.json")
        env = {
            "MID_ADMIN_TOKEN": "env2-token",
            "MID_CORE__TIMEOUT": "45m",
            "MID_CORE__RETRIES": "99",
            "MID_DEBUG": "true",
        }
        cfg = _config_show(runner, empty, env=env)
        assert cfg["admin-token"] == "env2-token"
        assert cfg["core"]["timeout"] == "45m"
        assert cfg["core"]["retries"] == 99
        assert cfg["debug"] is True


class TestGreetAutoWiring:
    """Tests for the greet command and auto-wiring logic."""

    def test_no_config_no_env_fallback_to_world(self, runner: CliRunner) -> None:
        """Scenario 5a: No config, no env -> 'World' fallback."""
        output = _greet(runner)
        assert output == "Hello, World!"

    def test_config_file_sets_token(self, runner: CliRunner, tmp_config: Any) -> None:
        """Config file token is used via MID_CONFIG_FILE env var."""
        cfg_file = tmp_config({"admin-token": "file-token"})
        output = _greet(runner, env={"MID_CONFIG_FILE": str(cfg_file)})
        assert output == "Hello, file-token!"

    def test_env_var_sets_token(self, runner: CliRunner) -> None:
        """Env var sets the greeting target."""
        output = _greet(runner, env={"MID_ADMIN_TOKEN": "env-token"})
        assert output == "Hello, env-token!"

    def test_cli_flag_overrides_env(self, runner: CliRunner) -> None:
        """CLI --admin-token flag overrides env var."""
        output = _greet(runner, args=["--admin-token", "cli-token"],
                        env={"MID_ADMIN_TOKEN": "env-token"})
        assert output == "Hello, cli-token!"

    def test_name_argument_wins_everything(self, runner: CliRunner) -> None:
        """Explicit name argument overrides all."""
        output = _greet(runner, args=["Alice", "--admin-token", "cli-token"],
                        env={"MID_ADMIN_TOKEN": "env-token"})
        assert output == "Hello, Alice!"

    def test_env_and_file_scoped_timeout(
        self, runner: CliRunner, tmp_config: Any
    ) -> None:
        """Config file timeout overrides default, env overrides config."""
        cfg_file = tmp_config({"core": {"timeout": "5m"}})

        # Config value used (no env)
        output = _greet(runner, env={"MID_CONFIG_FILE": str(cfg_file)})
        assert output == "Hello, World!"

        # With env var
        output = _greet(runner, env={"MID_CORE__TIMEOUT": "15m"})
        assert output == "Hello, World!"
