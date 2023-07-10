import pytest
import os

from jellyfin_client import JellyfinClient, PublicJellyfinClient, MediaItemType, JellyfinMediaItem
from jellyfin_croft import JellyfinCroft

HOST = os.environ.get("JELLYFIN_URI") or "http://jellyfin:8096"
USERNAME = os.environ.get("JELLYFIN_USERNAME")
PASSWORD = os.environ.get("JELLYFIN_PASSWORD")


class TestJellyfinCroft(object):

    def test_song_metadta_by_artist(self):
        artist = 'yalla'

        client = JellyfinClient(HOST, USERNAME, PASSWORD)
        response = client.search(artist, [MediaItemType.ARTIST.value])
        search_items = JellyfinCroft.parse_search_hints_from_response(response)
        artists = JellyfinMediaItem.from_list(search_items)
        assert len(artists) == 1
        artist_id = artists[0].id

        croft = JellyfinCroft(HOST, USERNAME, PASSWORD)
        songs = croft.get_songs_by_artist(artist_id)
        assert songs is not None and songs != []
        for song in songs:
            print(song)
            #assert artist in [a.lower() for a in song['Artists']]
