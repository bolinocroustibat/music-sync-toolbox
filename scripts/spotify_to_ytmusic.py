import sys
from pathlib import Path

from ytmusicapi import YTMusic
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from spotify import (
    Config as SpotifyConfig,
    setup_spotify,
    select_playlist as select_spotify_playlist,
    get_playlist_track_details as get_spotify_playlist_track_details,
)
from ytmusic import (
    Config as YTMusicConfig,
    setup_ytmusic,
    select_playlist as select_ytmusic_playlist,
    get_playlist_track_ids as get_ytmusic_playlist_track_ids,
    search_track as search_ytmusic_track,
    select_match as select_ytmusic_match,
    add_track_to_ytmusic,
)
from logger import FileLogger

logger = FileLogger(Path("scripts") / "spotify_to_ytmusic.log")


def process_tracks(
    ytm: YTMusic,
    tracks: list[dict],
    existing_tracks: set[str],
    ytmusic_playlist_id: str,
) -> tuple[int, int]:
    """Process all tracks and return counts of added and skipped tracks"""
    tracks_added = 0
    tracks_skipped = 0
    auto_first = False
    retry_delay = 5  # Initial delay in seconds

    logger.info("\nProcessing tracks...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing tracks...", total=len(tracks))
        for track in tracks:
            track_name = track["name"]
            artist_name = track["artist"]

            matches = search_ytmusic_track(ytm, track_name, artist_name)
            if matches:
                video_id = select_ytmusic_match(matches, auto_first)
                if video_id:
                    if video_id in existing_tracks:
                        logger.warning(
                            "Track already exists in YouTube Music playlist - skipping"
                        )
                        tracks_skipped += 1
                        progress.advance(task)
                        continue

                    success, retry_delay = add_track_to_ytmusic(
                        ytm, video_id, ytmusic_playlist_id, retry_delay
                    )
                    if success:
                        tracks_added += 1
                    else:
                        tracks_skipped += 1
                else:
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
            progress.advance(task)

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

    # Process tracks
    tracks_added, tracks_skipped = process_tracks(
        ytm, tracks, existing_tracks, ytmusic_playlist_id
    )

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to YouTube Music: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
