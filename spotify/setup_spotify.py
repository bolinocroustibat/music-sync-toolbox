import sys
from pathlib import Path

import spotipy
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth, SpotifyOauthError

from spotify.config import Config
from spotify.logger import logger

TOKEN_CACHE_PATH = Path("spotify") / ".spotify_token_cache"


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
        SystemExit: If authentication fails; the reason and how to fix it are logged.

    Note:
        This function will open a browser window for OAuth authentication
        if no valid cached token is found. The token is cached in
        spotify/.spotify_token_cache for future use. An expired or revoked
        cached token is discarded and the browser login is started again.
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

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=scope,
            open_browser=True,
            cache_handler=CacheFileHandler(cache_path=str(TOKEN_CACHE_PATH)),
            requests_timeout=30,
        ),
        requests_timeout=30,
    )

    try:
        user = _authenticate(sp)
    except SpotifyOauthError as e:
        _explain_oauth_error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Spotify authentication failed: {e}")
        logger.info("Check your [spotify] credentials in config.toml and your network connection.")
        sys.exit(1)

    logger.success(f"Successfully authenticated as: {user['display_name']}")
    return sp


def _authenticate(sp: spotipy.Spotify) -> dict:
    """Return the current user, logging in again once if the cached token is no longer valid."""
    try:
        return sp.current_user()
    except SpotifyOauthError as e:
        if e.error != "invalid_grant" or not TOKEN_CACHE_PATH.exists():
            raise
        logger.warning(f"Cached Spotify token is no longer valid ({e.error_description}).")
        logger.info("Discarding it and opening the browser to log in to Spotify again...")
        TOKEN_CACHE_PATH.unlink()
        return sp.current_user()


def _explain_oauth_error(e: SpotifyOauthError) -> None:
    """Log what went wrong during Spotify OAuth and how the user can fix it."""
    logger.error(f"Spotify authentication failed: {e.error_description or e.error or e}")
    if e.error == "invalid_client":
        logger.info("\nThe client_id / client_secret in config.toml were rejected by Spotify.")
        logger.info(
            "Copy them again from https://developer.spotify.com/dashboard (your app > Settings)."
        )
    elif e.error == "invalid_grant":
        logger.info(
            "\nThe login was not accepted. Run the command again and approve access in the browser."
        )
        logger.info(
            "The redirect_uri in config.toml must exactly match one listed in your app's settings."
        )
    logger.info(
        "\nIf the Spotify page itself shows 'Invalid redirect URI', add "
        "http://127.0.0.1:8888/callback to your app's Redirect URIs on "
        "https://developer.spotify.com/dashboard and use the same value as "
        "redirect_uri in config.toml (Spotify no longer accepts 'localhost')."
    )
