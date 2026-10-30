import sys
from pathlib import Path

from ytmusicapi import YTMusic

from logger import FileLogger
from scripts.playlist_sync import SyncMemory, filter_already_synced
from spotify import (
    Config as SpotifyConfig,
)
from spotify import (
    get_playlist_track_details as get_spotify_playlist_track_details,
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
    add_track_to_ytmusic,
    setup_ytmusic,
)
from ytmusic import (
    get_playlist_track_details as get_ytmusic_playlist_track_details,
)
from ytmusic import (
    get_playlist_track_ids as get_ytmusic_playlist_track_ids,
)
from ytmusic import (
    search_track as search_ytmusic_track,
)
from ytmusic import (
    select_match as select_ytmusic_match,
)
from ytmusic import (
    select_playlist as select_ytmusic_playlist,
)

logger = FileLogger(Path("scripts") / "spotify_to_ytmusic.log")


def process_tracks(
    ytm: YTMusic,
    tracks: list[dict],
    existing_tracks: set[str],
    ytmusic_playlist_id: str,
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

        matches = search_ytmusic_track(ytm, track_name, artist_name)
        if matches:
            video_id = select_ytmusic_match(matches, auto_first)
            if video_id:
                if video_id in existing_tracks:
                    logger.warning("Track already exists in YouTube Music playlist - skipping")
                    if memory:
                        memory.remember(track, video_id)
                    tracks_skipped += 1
                    continue

                success, retry_delay = add_track_to_ytmusic(
                    ytm, video_id, ytmusic_playlist_id, retry_delay
                )
                if success:
                    existing_tracks.add(video_id)
                    if memory:
                        memory.remember(track, video_id)
                    tracks_added += 1
                else:
                    tracks_skipped += 1
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

    # Get tracks from Spotify playlist
    tracks = get_spotify_playlist_track_details(sp, spotify_playlist_id)

    # Get existing tracks in YouTube Music playlist
    existing_tracks = get_ytmusic_playlist_track_ids(ytm, ytmusic_playlist_id)

    # Leave out tracks synced by a previous run
    memory = SyncMemory(ytmusic_playlist_id)
    destination_tracks = get_ytmusic_playlist_track_details(
        ytm, ytmusic_playlist_id, allow_empty=True
    )
    tracks, already_synced = filter_already_synced(tracks, destination_tracks, memory)
    logger.info(
        f"{already_synced} tracks already in the YouTube Music playlist, {len(tracks)} to sync"
    )

    # Process tracks
    tracks_added, tracks_skipped = process_tracks(
        ytm, tracks, existing_tracks, ytmusic_playlist_id, memory
    )

    # Print summary
    logger.info("\nSummary:")
    logger.info(f"Tracks already synced: {already_synced}")
    logger.success(f"Tracks added to YouTube Music: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
