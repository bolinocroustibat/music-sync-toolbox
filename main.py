import argparse
import sys
from pathlib import Path
import inquirer
import discogs_client as dc

from scripts.cli_helpers import activate_argcomplete, add_media_path_argument
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

ACTIONS_NEEDING_MEDIA_PATH = frozenset(
    {
        "discogs_update",
        "discogs_rename",
        "discogs_both",
        "spotify_add",
        "ytmusic_add",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Music Sync Toolbox — interactive menu for Spotify, YouTube Music, Discogs, and local files.",
    )
    add_media_path_argument(parser, required=False)
    activate_argcomplete(parser)
    return parser.parse_args()


def setup_config() -> tuple[DiscogsConfig, SpotifyConfig, YTMusicConfig]:
    """Load configuration from config.toml (must exist; see README and config.toml.example)."""
    if not CONFIG_PATH.is_file():
        discogs_logger.error(
            "No config.toml found. Copy config.toml.example to config.toml, edit it with your "
            "credentials, then run again. See README (Config section)."
        )
        sys.exit(1)

    discogs_config = DiscogsConfig()
    spotify_config = SpotifyConfig()
    ytmusic_config = YTMusicConfig()

    return discogs_config, spotify_config, ytmusic_config


def main() -> None:
    args = parse_args()

    discogs_config, _, _ = setup_config()

    ds = dc.Client("discogs_tag/0.5", user_token=discogs_config.token)

    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
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
    answers = inquirer.prompt(questions)
    if not answers:
        discogs_logger.error("No action selected")
        sys.exit(1)

    action = answers["action"]

    media_path: Path | None = None
    if action in ACTIONS_NEEDING_MEDIA_PATH:
        if args.path is None:
            discogs_logger.error(
                "This action requires a music directory. Pass --path / -p DIR (example: "
                "uv run music-sync --path ~/Music)."
            )
            sys.exit(1)
        media_path = args.path.expanduser().resolve()
        if not media_path.is_dir():
            discogs_logger.error(f"Media directory not found or not a directory: {media_path}")
            sys.exit(1)
        discogs_logger.info(f"\nUsing media directory: {media_path}\n")

    if action == "discogs_update":
        update_tags_from_discogs(media_path, discogs_config, ds)
    elif action == "discogs_rename":
        rename_files_from_tags(media_path)
    elif action == "discogs_both":
        discogs_logger.info("\nStep 1: Updating ID3 tags from Discogs...")
        update_tags_from_discogs(media_path, discogs_config, ds)
        discogs_logger.info("\nStep 2: Renaming files using updated ID3 tags...")
        rename_files_from_tags(media_path)
    elif action == "spotify_add":
        add_local_tracks_to_spotify(media_path)
    elif action == "ytmusic_add":
        add_local_tracks_to_ytmusic(media_path)
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
