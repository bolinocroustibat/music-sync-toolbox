import argparse
import sys
from pathlib import Path

import discogs_client as dc
import inquirer

from discogs import Config as DiscogsConfig
from local_files import logger as discogs_logger
from scripts import (
    add_local_tracks_to_spotify,
    add_local_tracks_to_ytmusic,
    download_from_soulseek,
    import_spotify_to_ytmusic,
    import_ytmusic_to_spotify,
    manage_spotify_duplicates,
)
from scripts.cli_helpers import activate_argcomplete, add_media_path_argument
from scripts.rename_files_from_tags import rename_files_from_tags
from scripts.update_tags_from_discogs import update_tags_from_discogs

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

# (icon, category, label, action). Icons are all double-width emoji without variation
# selectors (unlike e.g. 🏷️ or ➡️), so the columns line up in every terminal.
MENU = [
    ("🔖", "Local files", "Update ID3 tags from Discogs", "discogs_update"),
    ("📝", "Local files", "Rename files from their ID3 tags", "discogs_rename"),
    ("✨", "Local files", "Update ID3 tags from Discogs, then rename files", "discogs_both"),
    ("🟢", "Spotify", "Add local files to a playlist", "spotify_add"),
    ("🟢", "Spotify", "Import a YouTube Music playlist", "spotify_import"),
    ("🟢", "Spotify", "Find and remove duplicate tracks in a playlist", "spotify_duplicates"),
    ("🔴", "YouTube Music", "Add local files to a playlist", "ytmusic_add"),
    ("🔴", "YouTube Music", "Import a Spotify playlist", "ytmusic_import"),
    ("🐝", "Soulseek", "Search and download mp3/flac (via slskd)", "soulseek_download"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Music Sync Toolbox — interactive menu for Spotify, YouTube Music, Discogs, "
            "and local files."
        ),
    )
    add_media_path_argument(parser, required=False)
    activate_argcomplete(parser)
    return parser.parse_args()


def check_config() -> None:
    """Exit unless config.toml exists (see README and config.toml.example)."""
    if not CONFIG_PATH.is_file():
        discogs_logger.error(
            "No config.toml found. Copy config.toml.example to config.toml, edit it with your "
            "credentials, then run again. See README (Config section)."
        )
        sys.exit(1)


def setup_discogs() -> tuple[DiscogsConfig, dc.Client]:
    """Load the [discogs] config section and build an authenticated client."""
    discogs_config = DiscogsConfig()
    return discogs_config, dc.Client("discogs_tag/0.5", user_token=discogs_config.token)


def main() -> None:
    try:
        run()
    except KeyboardInterrupt:
        discogs_logger.warning("\nCancelled.")
        sys.exit(130)


def run() -> None:
    args = parse_args()

    check_config()

    category_width = max(len(category) for _, category, _, _ in MENU)
    questions = [
        inquirer.List(
            "action",
            message="What would you like to do?",
            choices=[
                (f"{icon}  {category.ljust(category_width)}   {label}", action)
                for icon, category, label, action in MENU
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
        update_tags_from_discogs(media_path, *setup_discogs())
    elif action == "discogs_rename":
        rename_files_from_tags(media_path)
    elif action == "discogs_both":
        discogs_logger.info("\nStep 1: Updating ID3 tags from Discogs...")
        update_tags_from_discogs(media_path, *setup_discogs())
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
