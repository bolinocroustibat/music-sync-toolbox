import time

import spotipy

from spotify.logger import logger


def add_track(
    sp: spotipy.Spotify,
    track_id: str,
    spotify_playlist_id: str,
    retry_delay: int,
) -> tuple[bool, int]:
    """Add track to Spotify playlist with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if spotify_playlist_id == "liked":
                # Special case for Liked Songs
                sp.current_user_saved_tracks_add([track_id])
            else:
                # Regular playlist
                sp.playlist_add_items(spotify_playlist_id, [track_id])
            logger.success("Track added to Spotify playlist.")
            time.sleep(2)  # Increased delay between requests
            return True, retry_delay
        except Exception as e:
            if "rate/request limit" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Rate limit reached. Waiting {retry_delay} seconds before retry..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error("Max retries reached for rate limit. Skipping track.")
                    return False, retry_delay
            else:
                logger.error(f"Error adding to Spotify playlist: {e}")
                logger.error(f"Track ID: {track_id}")
                logger.error(f"Playlist ID: {spotify_playlist_id}")
                return False, retry_delay
    return False, retry_delay
