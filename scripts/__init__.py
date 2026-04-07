# Import all main functions from script modules
from scripts.local_to_spotify import main as add_local_tracks_to_spotify
from scripts.local_to_ytmusic import main as add_local_tracks_to_ytmusic
from scripts.ytmusic_to_spotify import main as import_ytmusic_to_spotify
from scripts.spotify_to_ytmusic import main as import_spotify_to_ytmusic
from scripts.manage_spotify_duplicates import main as manage_spotify_duplicates
from scripts.soulseek_download import main as download_from_soulseek

__all__ = [
    "add_local_tracks_to_spotify",
    "add_local_tracks_to_ytmusic",
    "download_from_soulseek",
    "import_ytmusic_to_spotify",
    "import_spotify_to_ytmusic",
    "manage_spotify_duplicates",
]
