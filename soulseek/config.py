from pathlib import Path
import tomllib

TOML_PATH = Path("config.toml")


class SoulseekConfigError(Exception):
    """Raised when Soulseek (slskd API) configuration is missing or invalid."""


class Config:
    """Load slskd API settings from config.toml [soulseek] or legacy [slskd] section."""

    def __init__(self) -> None:
        if not TOML_PATH.exists():
            raise SoulseekConfigError(
                f"config.toml not found at {TOML_PATH.resolve()}. "
                "Copy config.toml.example and fill in [soulseek]."
            )

        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        if "soulseek" in config:
            section = config["soulseek"]
        elif "slskd" in config:
            section = config["slskd"]
        else:
            raise SoulseekConfigError(
                "Missing [soulseek] section in config.toml (or legacy [slskd]). "
                "See config.toml.example."
            )

        try:
            self.host = section["host"]
            self.api_key = section["api_key"]
        except KeyError as e:
            raise SoulseekConfigError(
                f"Missing required soulseek key in config.toml: {e.args[0]}"
            ) from e

        self.url_base = section.get("url_base", "/")
        self.verify_ssl = bool(section.get("verify_ssl", True))
        timeout = section.get("request_timeout")
        self.request_timeout = float(timeout) if timeout is not None else None
