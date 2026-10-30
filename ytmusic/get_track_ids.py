from ytmusicapi import YTMusic
from ytmusic.logger import logger


def get_playlist_track_ids(ytm: YTMusic, ytmusic_playlist_id: str) -> set[str]:
    """
    Get all track video IDs from a YouTube Music playlist.

    Args:
        ytm: Authenticated YTMusic client instance.
        ytmusic_playlist_id: Playlist ID.

    Returns:
        set[str]: Set of YouTube Music video IDs.

    Notes:
        - Works for Liked Music too ("LM").
    """
    logger.info("Fetching existing tracks from YouTube Music playlist...")
    existing_tracks: set[str] = set()
    results = ytm.get_playlist(ytmusic_playlist_id, limit=None)
    for track in results["tracks"]:
        if track.get("videoId"):
            existing_tracks.add(track["videoId"])
    return existing_tracks
