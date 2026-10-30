import pytest

from local_files import MusicFile, get_music_files, rename_file, sanitize_filename


class TestSanitizeFilename:
    def test_replaces_invalid_characters(self):
        assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_keeps_valid_characters(self):
        assert sanitize_filename("Daft Punk - One More Time (Edit)") == (
            "Daft Punk - One More Time (Edit)"
        )


class TestMusicFile:
    def test_reads_mp3_tags(self, make_mp3):
        music_file = MusicFile(make_mp3(artist="Artist", title="Title"))
        assert (music_file.artist, music_file.title) == ("Artist", "Title")

    def test_reads_flac_tags(self, make_flac):
        music_file = MusicFile(make_flac(artist="Artist", title="Title"))
        assert (music_file.artist, music_file.title) == ("Artist", "Title")

    def test_missing_tags_leave_empty_strings(self, make_mp3):
        music_file = MusicFile(make_mp3())
        assert (music_file.artist, music_file.title) == ("", "")

    @pytest.mark.xfail(reason="suffix compared case-sensitively; .FLAC hits ID3-only fallback")
    def test_reads_tags_with_uppercase_extension(self, make_flac):
        music_file = MusicFile(make_flac("TRACK.FLAC", artist="Artist", title="Title"))
        assert (music_file.artist, music_file.title) == ("Artist", "Title")


class TestGetMusicFiles:
    def test_filters_audio_files_recursively_and_sorts_by_name(
        self, tmp_path, make_mp3, make_flac
    ):
        sub = tmp_path / "sub"
        sub.mkdir()
        make_mp3("b.mp3")
        make_flac("A.flac", directory=sub)
        (tmp_path / "cover.jpg").write_bytes(b"")
        (tmp_path / "notes.txt").write_text("")

        names = [f.path.name for f in get_music_files(tmp_path)]

        assert names == ["A.flac", "b.mp3"]

    def test_non_recursive_ignores_subdirectories(self, tmp_path, make_mp3):
        sub = tmp_path / "sub"
        sub.mkdir()
        make_mp3("top.mp3")
        make_mp3("nested.mp3", directory=sub)

        names = [f.path.name for f in get_music_files(tmp_path, recursive=False)]

        assert names == ["top.mp3"]


class TestRenameFile:
    def test_renames_to_artist_dash_title(self, tmp_path, make_mp3):
        music_file = MusicFile(make_mp3("old.mp3", artist="AC/DC", title="T.N.T."))

        assert rename_file(music_file, confirm=False) == (True, False)
        assert (tmp_path / "AC_DC - T.N.T..mp3").is_file()
        assert not (tmp_path / "old.mp3").exists()

    def test_already_correct_name_is_untouched(self, make_mp3):
        music_file = MusicFile(make_mp3("A - T.mp3", artist="A", title="T"))
        assert rename_file(music_file, confirm=False) == (False, False)

    def test_existing_target_is_skipped(self, make_mp3):
        make_mp3("A - T.mp3")
        music_file = MusicFile(make_mp3("old.mp3", artist="A", title="T"))

        assert rename_file(music_file, confirm=False) == (False, True)
        assert music_file.path.exists()

    @pytest.mark.xfail(reason="rename_file does not update music_file.path")
    def test_updates_path_on_the_music_file(self, tmp_path, make_mp3):
        music_file = MusicFile(make_mp3("old.mp3", artist="A", title="T"))

        rename_file(music_file, confirm=False)

        assert music_file.path == tmp_path / "A - T.mp3"
