from pathlib import Path
import tomllib

TOML_PATH = Path("config.toml")


class Config:
    """Configuration manager for YouTube Music API credentials and settings.

    Loads YouTube Music-specific configuration from the main config.toml file,
    including OAuth credentials and optional playlist settings.
    """

    def __init__(self) -> None:
        """Initialize YouTube Music configuration from config.toml file.

        Loads the following configuration:
        - OAuth credentials (client_id, client_secret)
        - Optional playlist_id for default playlist selection

        Raises:
            FileNotFoundError: If config.toml file doesn't exist
            KeyError: If required YouTube Music configuration is missing
        """
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)

        ytmusic_config = config["ytmusic"]
        self.client_id = ytmusic_config["client_id"]
        self.client_secret = ytmusic_config["client_secret"]
        # Try to get playlist_id, None if not set
        self.playlist_id = ytmusic_config.get("playlist_id")
