"""In-memory stand-ins for the spotipy and ytmusicapi clients.

They follow the real APIs' paging and default limits closely enough that
code which forgets to paginate (or relies on a default limit) gets truncated
results, just like against the real services.
"""

from spotipy.exceptions import SpotifyException


def spotify_item(track_id, name="Song", artist="Artist", added_at="2024-01-01T00:00:00Z"):
    track = None
    if name is not None:
        track = {"id": track_id, "name": name, "artists": [{"name": artist}] if artist else []}
    return {"track": track, "added_at": added_at}


class FakeSpotify:
    def __init__(self, playlist=(), liked=(), playlists=(), search_results=()):
        self.playlist = list(playlist)
        self.liked = list(liked)
        self.playlists = list(playlists)
        self.search_results = list(search_results)
        self.added: list[tuple[str, list[str]]] = []
        self.saved: list[str] = []
        self.searches: list[str] = []

    # --- paging -------------------------------------------------------------
    def _page(self, source, offset, limit):
        items = source[offset : offset + limit]
        has_next = offset + limit < len(source)
        return {
            "items": items,
            "total": len(source),
            "next": f"next?offset={offset + limit}" if has_next else None,
            "_source": source,
            "_offset": offset + limit,
            "_limit": limit,
        }

    def next(self, page):
        if not page["next"]:
            return None
        return self._page(page["_source"], page["_offset"], page["_limit"])

    # --- reads --------------------------------------------------------------
    def current_user(self):
        return {"id": "me", "display_name": "Me"}

    def playlist_items(self, playlist_id, fields=None, limit=100, offset=0, **_):
        if playlist_id == "liked":
            raise SpotifyException(400, -1, "Invalid base62 id")
        return self._page(self.playlist, offset, limit)

    def current_user_saved_tracks(self, limit=20, offset=0, **_):
        return self._page(self.liked, offset, limit)

    def current_user_playlists(self, limit=50, offset=0):
        return self._page(self.playlists, offset, limit)

    def search(self, q, type="track", limit=10, **_):
        self.searches.append(q)
        return {"tracks": {"items": self.search_results[:limit]}}

    def track(self, track_id):
        raise AssertionError("search results already hold the name and artist")

    # --- writes -------------------------------------------------------------
    def playlist_add_items(self, playlist_id, items, position=None):
        self.added.append((playlist_id, list(items)))
        new = [spotify_item(_track_id(i), added_at="2099-01-01T00:00:00Z") for i in items]
        at = len(self.playlist) if position is None else position
        self.playlist[at:at] = new

    def current_user_saved_tracks_add(self, tracks):
        self.saved.extend(tracks)

    def playlist_remove_all_occurrences_of_items(self, playlist_id, items, snapshot_id=None):
        ids = {_track_id(i) for i in items}
        self.playlist = [
            it for it in self.playlist if not it["track"] or it["track"]["id"] not in ids
        ]

    def playlist_remove_specific_occurrences_of_items(self, playlist_id, items, snapshot_id=None):
        # Spotify silently ignores "positions" and removes every occurrence
        self.playlist_remove_all_occurrences_of_items(playlist_id, [i["uri"] for i in items])

    def remaining_ids(self):
        return [it["track"]["id"] for it in self.playlist if it["track"]]


def spotify_playlist(playlist_id, name=None, owner="me", collaborative=False, total=0):
    return {
        "id": playlist_id,
        "name": name or playlist_id,
        "owner": {"id": owner},
        "collaborative": collaborative,
        "tracks": {"total": total},
    }


def _track_id(uri_or_id):
    return uri_or_id.rsplit(":", 1)[-1]


def yt_track(video_id, title="Song", artist="Artist"):
    return {"videoId": video_id, "title": title, "artists": [{"name": artist}] if artist else []}


class FakeYTMusic:
    def __init__(self, playlist=(), liked=(), library=(), search_results=()):
        self.playlist = list(playlist)
        self.liked = list(liked)
        self.library = list(library)
        self.search_results = list(search_results)
        self.added: list[tuple[str, list[str]]] = []
        self.rated: list[tuple[str, str]] = []

    @staticmethod
    def _cap(items, limit):
        return items if limit is None else items[:limit]

    def get_playlist(self, playlist_id, limit=100, **_):
        tracks = self.liked if playlist_id == "LM" else self.playlist
        return {
            "title": "My playlist",
            "trackCount": len(tracks),
            "tracks": self._cap(tracks, limit),
        }

    def get_liked_songs(self, limit=100):
        return {
            "title": "Liked Music",
            "trackCount": len(self.liked),
            "tracks": self._cap(self.liked, limit),
        }

    def get_library_playlists(self, limit=25):
        return self._cap(self.library, limit)

    def search(self, query, filter=None, limit=20, **_):
        return self.search_results[:limit]

    def add_playlist_items(self, playlist_id, video_ids):
        self.added.append((playlist_id, list(video_ids)))

    def rate_song(self, video_id, rating):
        self.rated.append((video_id, rating))
