import sys
from pathlib import Path

import spotipy

from logger import FileLogger
from scripts.playlist_sync import SyncMemory, filter_already_synced
from spotify import (
    Config as SpotifyConfig,
)
from spotify import (
    add_track as add_track_to_spotify,
)
from spotify import (
    get_playlist_track_details as get_spotify_playlist_track_details,
)
from spotify import (
    get_playlist_track_ids as get_spotify_playlist_track_ids,
)
from spotify import (
    search_track as search_spotify_track,
)
from spotify import (
    select_playlist as select_spotify_playlist,
)
from spotify import (
    setup_spotify,
)
from ytmusic import (
    Config as YTMusicConfig,
)
from ytmusic import (
    get_playlist_track_details as get_ytmusic_playlist_track_details,
)
from ytmusic import (
    select_playlist as select_ytmusic_playlist,
)
from ytmusic import (
    setup_ytmusic,
)

logger = FileLogger(Path("scripts") / "ytmusic_to_spotify.log")


def process_tracks(
    sp: spotipy.Spotify,
    tracks: list[dict],
    existing_tracks: set[str],
    spotify_playlist_id: str,
    memory: SyncMemory | None = None,
) -> tuple[int, int]:
    """Process all tracks and return counts of added and skipped tracks"""
    tracks_added = 0
    tracks_skipped = 0
    auto_first = False
    retry_delay = 5  # Initial delay in seconds

    logger.info("\nProcessing tracks...")
    # No live progress bar: it would redraw over the match prompts
    for i, track in enumerate(tracks, 1):
        logger.info(f"\n[{i}/{len(tracks)}]")
        track_name = track["name"]
        artist_name = track["artist"]

        # Define search function with access to auto_first
        def search_with_auto_first(
            sp: spotipy.Spotify, track_name: str, artist_name: str
        ) -> str | None:
            nonlocal auto_first, retry_delay
            matches = search_spotify_track(sp, track_name, artist_name)
            if not matches:
                return None

            # Let user choose with 1 as default
            if auto_first:
                choice = "1"
            else:
                choice = (
                    input("\nSelect match number (1 is default, 's' to skip, 'a' for auto-first): ")
                    .strip()
                    .lower()
                )
                if choice == "a":
                    logger.info(
                        "Auto-first mode enabled - will select first match for all remaining tracks"
                    )
                    auto_first = True
                    choice = "1"

            if choice == "s":
                logger.warning("Track skipped")
                return None

            if choice == "" or choice == "1":
                choice = "1"

            if choice.isdigit() and 1 <= int(choice) <= len(matches):
                match = matches[int(choice) - 1]
                logger.success(f'Selected from Spotify: "{match["name"]} - {match["artist"]}"')
                return match["id"]

            logger.warning("Invalid choice - track skipped")
            return None

        track_id = search_with_auto_first(sp, track_name, artist_name)

        if track_id:
            if track_id in existing_tracks:
                logger.warning("Track already exists in Spotify playlist - skipping")
                if memory:
                    memory.remember(track, track_id)
                tracks_skipped += 1
                continue

            success, retry_delay = add_track_to_spotify(
                sp, track_id, spotify_playlist_id, retry_delay
            )
            if success:
                existing_tracks.add(track_id)
                if memory:
                    memory.remember(track, track_id)
                tracks_added += 1
            else:
                tracks_skipped += 1
        else:
            tracks_skipped += 1

    return tracks_added, tracks_skipped


def main() -> None:
    spotify_config = SpotifyConfig()
    ytmusic_config = YTMusicConfig()

    # Initialize YouTube Music client
    ytm = setup_ytmusic()

    # Get YouTube Music playlist ID from config or user selection
    ytmusic_playlist_id = select_ytmusic_playlist(ytm, ytmusic_config.playlist_id)

    # Initialize Spotify client
    sp = setup_spotify()

    # Get Spotify playlist ID from config or user selection
    spotify_playlist_id = select_spotify_playlist(sp, spotify_config.playlist_id)

    # Get tracks from YouTube Music playlist
    tracks = get_ytmusic_playlist_track_details(ytm, ytmusic_playlist_id)

    # Get existing tracks in Spotify playlist
    existing_tracks = get_spotify_playlist_track_ids(sp, spotify_playlist_id)

    # Leave out tracks synced by a previous run
    memory = SyncMemory(spotify_playlist_id)
    destination_tracks = get_spotify_playlist_track_details(
        sp, spotify_playlist_id, allow_empty=True
    )
    tracks, already_synced = filter_already_synced(tracks, destination_tracks, memory)
    logger.info(f"{already_synced} tracks already in the Spotify playlist, {len(tracks)} to sync")

    # Process tracks
    tracks_added, tracks_skipped = process_tracks(
        sp, tracks, existing_tracks, spotify_playlist_id, memory
    )

    # Print summary
    logger.info("\nSummary:")
    logger.info(f"Tracks already synced: {already_synced}")
    logger.success(f"Tracks added to Spotify: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
