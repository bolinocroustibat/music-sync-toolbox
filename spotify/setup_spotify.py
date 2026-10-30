import spotipy
from spotipy.oauth2 import SpotifyOAuth

from spotify.config import Config
from spotify.logger import logger


def setup_spotify() -> spotipy.Spotify:
    """Initialize and authenticate Spotify client with OAuth.

    Sets up a Spotify client with the following permissions:
    - playlist-modify-public: Modify public playlists
    - playlist-modify-private: Modify private playlists
    - playlist-read-private: Read private playlists
    - user-library-read: Read user's saved tracks
    - user-library-modify: Modify user's saved tracks

    Returns:
        spotipy.Spotify: Authenticated Spotify client instance

    Raises:
        Exception: If authentication fails or configuration is invalid

    Note:
        This function will open a browser window for OAuth authentication
        if no valid cached token is found. The token is cached in
        spotify/.spotify_token_cache for future use.
    """
    config = Config()
    scope = (
        "playlist-modify-public playlist-modify-private playlist-read-private "
        "user-library-read user-library-modify"
    )
    logger.info("Initializing Spotify client...")
    logger.info(f"Using client_id: {config.client_id}")
    logger.info(f"Using redirect_uri: {config.redirect_uri}")
    logger.info(f"Using scopes: {scope}")

    try:
        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri,
                scope=scope,
                open_browser=True,
                cache_path="spotify/.spotify_token_cache",
                requests_timeout=30,
            ),
            requests_timeout=30,
        )
        # Test the authentication
        user = sp.current_user()
        logger.success(f"Successfully authenticated as: {user['display_name']}")
        return sp
    except Exception as e:
        logger.error(f"Error during Spotify authentication: {e}")
        raise
