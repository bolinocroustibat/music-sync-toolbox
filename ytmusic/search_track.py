import time

from ytmusicapi import YTMusic

from ytmusic.logger import logger

MAX_MATCHES_TO_DISPLAY = 4  # Maximum number of matches to show for each track


def search_track(
    ytm: YTMusic, track_name: str, artist_name: str, file_name: str | None = None
) -> list[dict] | None:
    """
    Search for a track on YouTube Music using track name and artist.

    Args:
        ytm: Authenticated YTMusic client instance.
        track_name: Name of the track to search for.
        artist_name: Name of the artist to search for.
        file_name: Optional name of the local file being processed (for logging).

    Returns:
        list[dict] | None: List of potential matches, each containing:
            - id: YouTube Music video ID
            - name: Track title
            - artist: Artist name
            Returns None if no matches found or search fails.

    Notes:
        - Maximum of 4 matches are returned (MAX_MATCHES_TO_DISPLAY).
        - Retries up to 3 times on rate limit errors, with exponential backoff.
        - If track_name or artist_name is empty, returns None immediately.
    """
    if not track_name or not artist_name:
        if file_name:
            logger.error(f"Missing tags for local file {file_name}")
        return None

    query = f"{track_name} {artist_name}"
    if file_name:
        logger.info(f'\nLocal file: "{file_name}"')
    logger.info(f'\nSearching YouTube Music for "{track_name} - {artist_name}"')

    max_retries = 3
    retry_delay = 5  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            results = ytm.search(query, filter="songs", limit=5)
            if not results:
                logger.error("No matches found on YouTube Music")
                return None

            # Format matches
            matches: list[dict] = []
            for track in results:
                if not track.get("videoId") or not track.get("title") or not track.get("artists"):
                    continue

                matches.append(
                    {
                        "id": track["videoId"],
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )

            if not matches:
                logger.error("No valid matches found on YouTube Music")
                return None

            # Only return first N matches
            return matches[:MAX_MATCHES_TO_DISPLAY]

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
                    logger.error("Max retries reached for rate limit.")
                    return None
            else:
                logger.error(f"Error searching YouTube Music: {e}")
                logger.error(f"Query was: {query}")
                return None

    return None
