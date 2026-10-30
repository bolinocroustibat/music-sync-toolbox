from ytmusicapi import YTMusic

from ytmusic.logger import logger


def create_playlist(ytm: YTMusic, name: str, description: str = "") -> str:
    """
    Create a new YouTube Music playlist.

    Args:
        ytm: Authenticated YTMusic client instance.
        name: Name of the playlist to create.
        description: Optional description for the playlist.

    Returns:
        str: ID of the created playlist.

    Raises:
        Exception: If playlist creation fails or response is invalid.

    Notes:
        - The playlist will be created under the authenticated user's account.
        - Returns the playlist ID which can be used for future operations.
    """
    try:
        logger.info(f'Creating new YouTube Music playlist "{name}"...')
        result = ytm.create_playlist(name, description)
        playlist_id = result if isinstance(result, str) else result.get("playlistId")
        if not playlist_id:
            raise RuntimeError("Failed to get playlist ID from response")
        logger.success(f'Created playlist "{name}" with ID: {playlist_id}')
        return playlist_id
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        raise
