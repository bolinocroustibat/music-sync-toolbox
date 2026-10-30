import time

from ytmusicapi import YTMusic

from ytmusic.logger import logger


def add_track_to_ytmusic(
    ytm: YTMusic,
    video_id: str,
    ytmusic_playlist_id: str,
    retry_delay: int,
) -> tuple[bool, int]:
    """
    Add a track to a YouTube Music playlist with retry logic for rate limits.

    Args:
        ytm: Authenticated YTMusic client instance.
        video_id: YouTube Music video ID to add.
        ytmusic_playlist_id: Target playlist ID, or "LM" for Liked Music.
        retry_delay: Initial delay (in seconds) between retries on rate limit.

    Returns:
        tuple[bool, int]: (success, final retry_delay). Success is True if the track was added.

    Notes:
        - Retries up to 3 times on rate limit errors, with exponential backoff.
        - Returns False if all retries fail or another error occurs.
        - Uses `rate_song` for Liked Music, `add_playlist_items` for regular playlists.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if ytmusic_playlist_id == "LM":
                # Special case for Liked Music - use rate_song instead of add_playlist_items
                ytm.rate_song(video_id, "LIKE")
            else:
                # Regular playlist
                ytm.add_playlist_items(ytmusic_playlist_id, [video_id])
            logger.success("Track added to YouTube Music playlist.")
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
                logger.error(f"Error adding to YouTube Music playlist: {e}")
                logger.error(f"Video ID: {video_id}")
                logger.error(f"Playlist ID: {ytmusic_playlist_id}")
                return False, retry_delay
    return False, retry_delay
