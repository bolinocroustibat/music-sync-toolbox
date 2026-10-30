import json
import sys
from pathlib import Path

import inquirer
from ytmusicapi import OAuthCredentials, YTMusic

from ytmusic.config import Config
from ytmusic.logger import logger

OAUTH_PATH = Path("ytmusic") / "oauth.json"
BROWSER_PATH = Path("ytmusic") / "browser.json"


def setup_ytmusic() -> YTMusic:
    """
    Initialize and authenticate YouTube Music client.

    Sets up a YTMusic client using either OAuth or browser cookie authentication
    based on user preference and available credentials.

    Returns:
        YTMusic: Authenticated YTMusic client instance.

    Raises:
        SystemExit: If authentication fails; the reason and how to fix it are logged.

    Notes:
        - Prompts user to choose between browser cookies and OAuth authentication.
        - OAuth requires client_id and client_secret in config.toml.
        - Browser authentication requires browser.json file with cookies.
        - YouTube Music currently rejects most OAuth requests (HTTP 400), so
          browser cookies are the recommended method.
    """
    auth_method = choose_auth_method()

    if auth_method == "oauth":
        check_ytmusic_setup_oauth()
        config = Config()
        oauth_credentials = OAuthCredentials(
            client_id=config.client_id, client_secret=config.client_secret
        )
        try:
            ytm = YTMusic(str(OAUTH_PATH), oauth_credentials=oauth_credentials)
            ytm.get_library_playlists(limit=1)
            logger.success("YouTube Music authentication successful")
            return ytm
        except Exception as e:
            _explain_oauth_error(e)
            if not BROWSER_PATH.is_file():
                sys.exit(1)
            logger.warning(f"\nFalling back to browser cookies from {BROWSER_PATH}...")

    check_ytmusic_setup_browser()
    try:
        ytm = YTMusic(str(BROWSER_PATH))
        ytm.get_library_playlists(limit=1)
    except Exception as e:
        _explain_browser_error(e)
        sys.exit(1)

    logger.success("YouTube Music authentication successful")
    return ytm


def _explain_oauth_error(e: Exception) -> None:
    """Log why OAuth authentication failed and how the user can fix it."""
    if isinstance(e, KeyError) and "access_token" in str(e):
        logger.error("OAuth token refresh failed: the refresh token is invalid or expired.")
        logger.info("\nRegenerate it in your terminal (it needs your keyboard and a browser):")
        logger.info(f"  uv run ytmusicapi oauth --file {OAUTH_PATH}")
        logger.info("Use the same client_id and client_secret as in config.toml.")
        logger.info(
            "If your Google Cloud OAuth app is in 'Testing' mode, its tokens expire after "
            "7 days: publish it ('In production') on the OAuth consent screen."
        )
    elif "HTTP 400" in str(e):
        logger.error(f"YouTube Music rejected the OAuth request: {e}")
        logger.info(
            "\nThis is a known YouTube Music limitation with OAuth, regenerating the token "
            "will not help. Use 'Browser Cookies' authentication instead."
        )
        if not BROWSER_PATH.is_file():
            _log_browser_setup_instructions()
    else:
        logger.error(f"YouTube Music OAuth authentication failed: {e}")
        logger.info(
            f"\nTry regenerating your OAuth token: uv run ytmusicapi oauth --file {OAUTH_PATH}"
        )
        logger.info("Or use 'Browser Cookies' authentication instead.")


def _explain_browser_error(e: Exception) -> None:
    """Log why browser cookie authentication failed and how the user can fix it."""
    logger.error(f"YouTube Music browser authentication failed: {e}")
    logger.info(
        f"\nThe cookies in {BROWSER_PATH} are probably expired (e.g. you logged out of Google "
        "in that browser). Create the file again:"
    )
    _log_browser_setup_instructions()


def _log_browser_setup_instructions() -> None:
    logger.info(
        "1. Open https://music.youtube.com logged in with the account holding your playlists"
    )
    logger.info(
        "2. Open the developer tools > Network tab, filter on 'browse', click a POST request"
    )
    logger.info("3. Copy its request headers (Chrome: Headers > Request Headers > Raw)")
    logger.info(f"4. Run: uv run ytmusicapi browser --file {BROWSER_PATH}")
    logger.info("   paste the headers, press Enter then Ctrl-D")
    logger.info("Details: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")


def choose_auth_method() -> str:
    """
    Let the user choose between OAuth and browser cookie authentication.

    Returns:
        str: The chosen authentication method ("oauth" or "browser").

    Raises:
        KeyboardInterrupt: If user cancels the selection process.

    Notes:
        - Browser cookies are recommended: YouTube Music currently rejects most OAuth requests.
        - Browser authentication uses saved cookies from a browser session.
    """
    questions = [
        inquirer.List(
            "auth_method",
            message="Choose YouTube Music authentication method",
            choices=[
                ("Browser Cookies (recommended)", "browser"),
                ("OAuth", "oauth"),
            ],
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Authentication method selection cancelled")
    return answers["auth_method"]


def check_ytmusic_setup_oauth() -> None:
    """
    Check if YouTube Music OAuth authentication is properly configured.

    Verifies that OAuth credentials are set up in config.toml and that
    the oauth.json file exists with valid authentication tokens.

    Raises:
        SystemExit: If OAuth setup is incomplete or invalid.

    Notes:
        - Checks for client_id and client_secret in config.toml.
        - Verifies oauth.json file exists.
        - Provides detailed setup instructions if configuration is missing.
    """
    config = Config()
    if not config.client_id or not config.client_secret:
        logger.error("YouTube Music OAuth credentials not set up.")
        logger.info("\nTo set up YouTube Music OAuth authentication:")
        logger.info("1. Go to https://console.cloud.google.com")
        logger.info("2. Create a new project or select an existing one")
        logger.info("3. Enable the YouTube Data API v3")
        logger.info("4. Go to APIs & Services > OAuth consent screen")
        logger.info("   - Set User Type to 'External'")
        logger.info("   - Fill in required fields (App name, User support email, etc.)")
        logger.info("   - Add your Google account email under 'Test users'")
        logger.info("5. Go to APIs & Services > Credentials")
        logger.info("   - Create OAuth 2.0 Client ID")
        logger.info("   - Select 'TVs and Limited Input devices' as the application type")
        logger.info("   - Copy the Client ID and Client Secret")
        logger.info("\nThen add them to your config.toml file:")
        logger.info("[ytmusic]")
        logger.info("client_id = YOUR_CLIENT_ID")
        logger.info("client_secret = YOUR_CLIENT_SECRET")
        logger.info(
            "\nAfter that, run 'uv run ytmusicapi oauth' in your terminal to create oauth.json"
        )
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)

    if not OAUTH_PATH.is_file():
        logger.error("oauth.json file not found.")
        logger.info(f"\nRun 'uv run ytmusicapi oauth' in your terminal to create {OAUTH_PATH}")
        logger.info("Follow the instructions to complete the OAuth flow")
        sys.exit(1)

    # Validate oauth.json file structure
    try:
        with open(OAUTH_PATH) as f:
            oauth_data = json.load(f)
            if "access_token" not in oauth_data and "token" not in oauth_data:
                logger.error("oauth.json file is missing required token fields.")
                logger.error(f"Expected 'access_token' or 'token' field in {OAUTH_PATH}")
                logger.info("\nThe oauth.json file appears to be invalid or expired.")
                logger.info("Run 'uv run ytmusicapi oauth' to regenerate the OAuth token.")
                sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"oauth.json file is not valid JSON: {e}")
        logger.info("\nRun 'uv run ytmusicapi oauth' to regenerate the OAuth token.")
        sys.exit(1)
    except Exception as e:
        logger.warning(f"Could not validate oauth.json structure: {e}")

    logger.success(f"Found oauth.json at: {OAUTH_PATH}")


def check_ytmusic_setup_browser() -> None:
    """
    Check if YouTube Music browser authentication is properly configured.

    Verifies that the browser.json file exists with valid browser cookies
    for YouTube Music authentication.

    Raises:
        SystemExit: If browser setup is incomplete or invalid.

    Notes:
        - Checks for browser.json file in the ytmusic directory.
        - Provides setup instructions if the file is missing.
        - References external documentation for detailed setup steps.
    """
    if not BROWSER_PATH.is_file():
        logger.error("browser.json file not found.")
        logger.info("\nTo set up YouTube Music browser authentication:")
        _log_browser_setup_instructions()
        sys.exit(1)
    logger.success(f"Found browser.json at: {BROWSER_PATH}")
