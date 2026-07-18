import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, get_args, get_origin

from pydantic import BaseModel, Field

APP_NAME = "mid"


class CoreConfig(BaseModel):
    timeout: str = "2m"
    retries: int = 3


class AppSettings(BaseModel):
    admin_token: Optional[str] = None
    debug: bool = False
    dry_run: bool = False
    core: CoreConfig = Field(default_factory=CoreConfig)

    @classmethod
    def _env_key(cls, *parts: str) -> str:
        joined = "__".join(p.upper() for p in parts)
        return f"{APP_NAME.upper()}_{joined}"

    @classmethod
    def _resolve_path(cls, config_path: Optional[Path]) -> Path:
        if config_path:
            return config_path
        path_env = os.environ.get(cls._env_key("CONFIG_FILE"))
        if path_env:
            return Path(path_env)
        local = Path(f"{APP_NAME}.json")
        if local.exists():
            return local
        xdg = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            / APP_NAME
            / f"{APP_NAME}.json"
        )
        return xdg

    @classmethod
    def _resolve_type(cls, raw_type: type) -> type:
        origin = get_origin(raw_type)
        if origin is not None:
            args = get_args(raw_type)
            # For Optional[X] which is Union[X, None], get the non-None type
            non_none = [a for a in args if a is not type(None)]  # noqa: E721
            if non_none:
                return cls._resolve_type(non_none[0])
        return raw_type

    @classmethod
    def _coerce(cls, value: str, target_type: type) -> Any:
        if target_type is bool:
            return value.lower() in ("true", "1", "yes")
        if target_type is int:
            return int(value)
        return value

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AppSettings":
        path = cls._resolve_path(config_path)

        instance = cls()

        raw: Dict[str, Any] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except (json.JSONDecodeError, IOError):
                pass

        # Merge file values — only where no env var exists
        def _apply_file(
            parts: tuple[str, ...], target: Any, data: Dict[str, Any]
        ) -> None:
            for key, value in data.items():
                snake = key.replace("-", "_")
                if not hasattr(target, snake):
                    continue
                env_key = cls._env_key(*parts, snake)
                if os.environ.get(env_key) is not None:
                    continue
                sub = getattr(target, snake)
                if isinstance(sub, BaseModel) and isinstance(value, dict):
                    _apply_file((*parts, snake), sub, value)
                else:
                    setattr(target, snake, value)

        _apply_file((), instance, raw)

        # Apply top-level env vars
        for field_name in cls.model_fields:
            env_key = cls._env_key(field_name)
            if env_val := os.environ.get(env_key):
                raw_type = cls.model_fields[field_name].annotation
                if raw_type is not None:
                    target_type = cls._resolve_type(raw_type)
                    setattr(instance, field_name, cls._coerce(env_val, target_type))

        # Apply nested env vars (e.g. MID_CORE__TIMEOUT)
        for field_name in cls.model_fields:
            sub = getattr(instance, field_name)
            sub_type = cls.model_fields[field_name].annotation
            if sub_type is None:
                continue
            resolved_sub = cls._resolve_type(sub_type)
            if hasattr(resolved_sub, "model_fields"):
                for sub_name in resolved_sub.model_fields:
                    sub_env = cls._env_key(field_name, sub_name)
                    if sub_val := os.environ.get(sub_env):
                        sub_raw_type = resolved_sub.model_fields[sub_name].annotation
                        if sub_raw_type is not None:
                            target_sub_type = cls._resolve_type(sub_raw_type)
                            setattr(
                                sub, sub_name,
                                cls._coerce(sub_val, target_sub_type),
                            )

        return instance

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
