# Music Sync Toolbox

A CLI toolbox for syncing your music across Spotify, YouTube Music and local music files, using Discogs as a source of truth.
Features include:
- Metadata enrichment and local music files management using Discogs database
- Bidirectional playlist synchronization between Spotify and YouTube Music
- Automatic duplicate detection and removal in Spotify and YouTube Music playlists
- Import of local music files into Spotify and YouTube Music playlists

## Prerequisites

- Requires Python >=3.10 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- For the Discogs tag updater, it requires a Discogs developper account and free API key: [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)
- For Spotify integration: requires a Spotify Developer account: [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
- For YouTube Music integration: it requires either:
  - A YouTube Music Developer account: [https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials](https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials)
  - Or a YouTube Music session cookie file (see [https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)), but this might not be working as expected.
- For Soulseek downloads (menu “via slskd”): a **running [slskd](https://github.com/slskd/slskd)** daemon. It is not a Python package in this repo; install slskd separately (see [Soulseek (slskd)](#soulseek-slskd) below).

## Install
```sh
uv sync
cp config.toml.example config.toml
# Edit config.toml with your API credentials (see Config below)
```

## Usage
```sh
uv run music-sync --path /path/to/your/music
```

Pass `--path` / `-p` when you pick an action that scans local files (Discogs tagging, rename from tags, add local tracks to Spotify or YouTube Music). Other menu options do not need it.

For shell tab-completion on the music directory (requires [argcomplete](https://github.com/kislyuk/argcomplete)), install the hook once, for example:

```sh
eval "$(register-python-argcomplete music-sync)"
eval "$(register-python-argcomplete music-sync-toolbox)"
```

Add that line to your `~/.zshrc` or `~/.bashrc` if you want it permanently (use the script name you actually run).

The command opens an interactive menu of features.

## Config
Before the first run, copy `config.toml.example` to `config.toml` in the project directory and fill in your credentials. You can adjust options later by editing `config.toml` (see the **Options** section below for field meanings).

### Local music directory
Pass the folder that contains your audio files on the command line with `--path` / `-p` whenever you run an action that needs it (see Usage). It is not stored in `config.toml`. If you upgrade from an older version, remove the `[local_files]` section from `config.toml` if it is still present.

### Discogs Setup
For the discogs access token, you can create one [here](https://www.discogs.com/settings/developers).

### Spotify Setup
1. Create an application in your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Get your `client_id` and `client_secret` from the application settings
3. Add `http://localhost:8888/callback` to the Redirect URIs in your application settings
4. Get your target playlist ID (the last part of the playlist URL: spotify:playlist:**YOUR_PLAYLIST_ID**)

### YouTube Music Setup
You can choose between two authentication methods:

1. OAuth (Recommended):
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials (TVs and Limited Input devices type)
   - Add your credentials to `config.toml`
   - Run `uv run ytmusicapi oauth` to create `oauth.json`

2. Browser Cookies:
   - Follow the instructions at [ytmusicapi browser setup](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)
   - Create a `browser.json` file with your browser credentials

### Soulseek (slskd)

The Soulseek menu uses slskd’s **REST API**. You do **not** need the classic Soulseek GUI client; you need **slskd** installed, configured, and running on your machine (or reachable on your network).

#### Install slskd

Follow the upstream project: **[slskd on GitHub](https://github.com/slskd/slskd)**. Common options:

1. **Docker** (official image `slskd/slskd`):
   - Quick start and port layout are in the [README Quick Start](https://github.com/slskd/slskd#quick-start) (HTTP **5030**, HTTPS **5031**, listening **50300**).
   - More detail: [Docker guide](https://github.com/slskd/slskd/blob/master/docs/docker.md).

2. **Pre-built binaries**:
   - Download a release for your OS from [GitHub Releases](https://github.com/slskd/slskd/releases), unzip, and run the binary.
   - On first run, slskd creates a data directory and `slskd.yml` (e.g. under `~/.local/share/slskd` on Linux/macOS, or `%LocalAppData%\slskd` on Windows).

#### Configure slskd for this toolbox

1. Complete Soulseek **username/password** (and shares/downloads) in slskd using the **web UI** (default login is often `slskd` / `slskd` until you change it) or by editing `slskd.yml`.
2. Enable **API authentication** in slskd and set an **API key**; put the same value in `config.toml` as `[soulseek].api_key`.
3. Set `[soulseek].host` to match how you reach the API (the example uses `https://127.0.0.1:5031`). If you use a self-signed certificate, you may need `verify_ssl = false` in `config.toml` (see comments in `config.toml.example`).
4. Downloads are handled entirely by slskd; files land in slskd’s configured download directory.

Full slskd options: **[configuration reference](https://github.com/slskd/slskd/blob/master/docs/config.md)** and **[example YAML](https://github.com/slskd/slskd/blob/master/config/slskd.example.yml)**.

## Options

### Command line
`--path` / `-p DIR`  
Directory containing your music files. Required when you choose a menu action that scans local files.

### Discogs (`config.toml` — 💿) Options
`token`  
Your Discogs API token.

`overwrite_year = false`
If year tag is set on the file, it will not overwrite it.  
If year tag is empty, it will add it.

`overwrite_genre = false`
If genre tag is set on the file, it will not overwrite it.  
If genre tag is empty, it will add it.  

`embed_cover = true`
Enable or disable cover embedding feature. Will overwrite existing covers.

`overwrite_cover = false`
If cover is set on the file, it will not overwrite it.  
If cover is empty, it will add it.

`rename_file = false`
If file is already named correctly, it will not rename it.
If artist and/or title is empty, it will not rename it.
Otherwise, it will rename it to `artist - title.ext`.

### Spotify (🟢) Options
`client_id`  
Your Spotify application client ID.

`client_secret`  
Your Spotify application client secret.

`redirect_uri`  
The redirect URI for OAuth authentication (default: http://localhost:8888/callback).

`playlist_id`  
The ID of the playlist where you want to add tracks. If not set, you'll be prompted to select a playlist when running the script.

### YouTube Music (🔴) Options
`client_id`  
Your YouTube Music OAuth client ID (only needed for OAuth method).

`client_secret`  
Your YouTube Music OAuth client secret (only needed for OAuth method).

`playlist_id`  
The ID of the playlist where you want to add tracks. If not set, you'll be prompted to select a playlist when running the script.

### Soulseek (`config.toml`)

`host`  
Base URL of the slskd API (e.g. `https://127.0.0.1:5031`).

`api_key`  
Must match the API key configured in slskd.

Optional keys (`url_base`, `verify_ssl`, `request_timeout`) are documented in `config.toml.example`.

## TODO

### Spotify (🟢) Improvements
- In `spotify/add_tracks.py`: Compare Spotify matches with local files BEFORE asking user for match selection
  - This will help identify the best match automatically
  - Only ask user if no exact match is found

### Code Refactoring for Django Backend
- Refactor core functionality to be framework-agnostic:
  - Move all business logic into separate service classes
  - Return structured responses with success/error messages and data
  - Remove direct CLI interactions (print, input) from core functions
  - Create separate handlers for CLI and web interfaces
- Example structure:
  ```python
  class TagUpdaterService:
      def update_tags(self, file_path: Path) -> dict:
          return {
              "success": bool,
              "message": str,
              "data": {
                  "genres_updated": bool,
                  "year_updated": bool,
                  "cover_updated": bool,
                  "file_renamed": bool,
                  "new_path": str | None
              }
          }
  ```
- Benefits:
  - Same core code can be used in CLI and web interface
  - Better error handling and reporting
  - Easier to test individual components
  - Progress updates can be sent to web interface via WebSocket
  - Configuration can be stored in database instead of files
