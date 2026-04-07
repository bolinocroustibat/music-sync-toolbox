import sys
from pathlib import Path
import inquirer
from inquirer_prompt import prompt
import tomllib
import discogs_client as dc

from discogs import Config as DiscogsConfig
from local_files import logger as discogs_logger
from scripts.update_tags_from_discogs import update_tags_from_discogs
from scripts.rename_files_from_tags import rename_files_from_tags

from spotify import Config as SpotifyConfig
from ytmusic import Config as YTMusicConfig
from scripts import (
    add_local_tracks_to_spotify,
    add_local_tracks_to_ytmusic,
    download_from_soulseek,
    import_ytmusic_to_spotify,
    import_spotify_to_ytmusic,
    manage_spotify_duplicates,
)

CONFIG_PATH = Path("config.toml")


def setup_config() -> tuple[DiscogsConfig, SpotifyConfig, YTMusicConfig]:
    """Initialize or create configuration for all services."""
    if not CONFIG_PATH.exists():
        discogs_logger.info("No config.toml file found. Let's create one!")
        config_data = {}

        # Get media path
        questions = [
            inquirer.Text(
                "media_path",
                message="Enter the path to your music files directory",
                default=str(Path.home() / "Music"),
            ),
        ]
        answers = prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data["media_path"] = answers["media_path"]

        # Get Discogs token
        questions = [
            inquirer.Text(
                "token",
                message="Enter your Discogs token",
            ),
        ]
        answers = prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Get Spotify credentials
        questions = [
            inquirer.Text(
                "client_id",
                message="Enter your Spotify client ID",
            ),
            inquirer.Text(
                "client_secret",
                message="Enter your Spotify client secret",
            ),
            inquirer.Text(
                "redirect_uri",
                message="Enter your Spotify redirect URI",
                default="http://localhost:8888/callback",
            ),
        ]
        answers = prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Get YouTube Music credentials
        questions = [
            inquirer.Text(
                "client_id",
                message="Enter your YouTube Music client ID",
            ),
            inquirer.Text(
                "client_secret",
                message="Enter your YouTube Music client secret",
            ),
        ]
        answers = prompt(questions)
        if not answers:
            discogs_logger.error("Configuration cancelled by user")
            sys.exit(1)
        config_data.update(answers)

        # Write config file
        DiscogsConfig.write(config_data)
        discogs_logger.info(f"Configuration saved to {CONFIG_PATH}")

    # Initialize configs
    discogs_config = DiscogsConfig()
    spotify_config = SpotifyConfig()
    ytmusic_config = YTMusicConfig()

    return discogs_config, spotify_config, ytmusic_config


def setup_media_path() -> Path:
    """Setup media path if not defined in config."""
    discogs_logger.info("Media path not found in config. Let's set it up!")
    questions = [
        inquirer.Text(
            "media_path",
            message="Enter the path to your music files directory",
            default=str(Path.home() / "Music"),
        ),
    ]
    answers = prompt(questions)
    if not answers:
        discogs_logger.error("Configuration cancelled by user")
        sys.exit(1)

    # Read existing config
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)

    # Update only the path in the local_files section
    if "local_files" not in config:
        config["local_files"] = {}
    config["local_files"]["path"] = answers["media_path"]

    # Write back the updated config
    with open(CONFIG_PATH, "w") as f:
        f.write("[local_files]\n")
        f.write(f'path = "{config["local_files"]["path"]}"\n\n')

        # Write discogs section
        if "discogs" in config:
            f.write("[discogs]\n")
            for key, value in config["discogs"].items():
                if isinstance(value, bool):
                    f.write(f"{key} = {str(value).lower()}\n")
                else:
                    f.write(f'{key} = "{value}"\n')
            f.write("\n")

        # Write spotify section
        if "spotify" in config:
            f.write("[spotify]\n")
            for key, value in config["spotify"].items():
                f.write(f'{key} = "{value}"\n')
            f.write("\n")

        # Write ytmusic section
        if "ytmusic" in config:
            f.write("[ytmusic]\n")
            for key, value in config["ytmusic"].items():
                f.write(f'{key} = "{value}"\n')

    return Path(answers["media_path"])


def main() -> None:
    # Setup configurations
    discogs_config, spotify_config, ytmusic_config = setup_config()

    # Initialize Discogs client
    ds = dc.Client("discogs_tag/0.5", user_token=discogs_config.token)

    # Show menu
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                # Discogs options
                (
                    "💿  ➡️  🏷️  Update ID3 tags of the local files using Discogs",
                    "discogs_update",
                ),
                (
                    "🏷️  ➡️  📁  Rename files using their ID3 tags",
                    "discogs_rename",
                ),
                (
                    "💿  ➡️  🏷️  ➡️  📁  Update ID3 tags and rename files",
                    "discogs_both",
                ),
                # Spotify options
                (
                    "🟢  ➕  Add local files to Spotify playlist",
                    "spotify_add",
                ),
                (
                    "🔴  ➡️  🟢  Import tracks from YouTube Music playlist to Spotify Playlist",
                    "spotify_import",
                ),
                (
                    "🟢  🧹  Find and remove duplicate tracks in Spotify playlist",
                    "spotify_duplicates",
                ),
                # YouTube Music options
                (
                    "🔴  ➕  Add local files to YouTube Music playlist",
                    "ytmusic_add",
                ),
                (
                    "🟢  ➡️  🔴  Import tracks from Spotify playlist to YouTube Music Playlist",
                    "ytmusic_import",
                ),
                (
                    "🐝  ⬇️  Search Soulseek and download mp3/flac (via slskd)",
                    "soulseek_download",
                ),
            ],
        ),
    ]
    answers = prompt(questions)
    if not answers:
        discogs_logger.error("No action selected")
        sys.exit(1)

    # Execute selected action
    action = answers["action"]

    # Check media path for features that need it
    if action in [
        "discogs_update",
        "discogs_rename",
        "discogs_both",
        "spotify_add",
        "ytmusic_add",
    ]:
        if not discogs_config.media_path:
            media_path = setup_media_path()
        else:
            media_path = discogs_config.media_path
        discogs_logger.info(f"\nUsing media directory: {media_path}\n")

    if action == "discogs_update":
        update_tags_from_discogs(media_path, discogs_config, ds)
    elif action == "discogs_rename":
        rename_files_from_tags()
    elif action == "discogs_both":
        discogs_logger.info("\nStep 1: Updating ID3 tags from Discogs...")
        update_tags_from_discogs(media_path, discogs_config, ds)
        discogs_logger.info("\nStep 2: Renaming files using updated ID3 tags...")
        rename_files_from_tags()
    elif action == "spotify_add":
        add_local_tracks_to_spotify()
    elif action == "ytmusic_add":
        add_local_tracks_to_ytmusic()
    elif action == "spotify_import":
        import_ytmusic_to_spotify()
    elif action == "spotify_duplicates":
        manage_spotify_duplicates()
    elif action == "ytmusic_import":
        import_spotify_to_ytmusic()
    elif action == "soulseek_download":
        download_from_soulseek()


if __name__ == "__main__":
    main()
