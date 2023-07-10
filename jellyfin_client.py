import logging
import requests
from enum import Enum

# url constants
AUTHENTICATE_BY_NAME_URL = "/Users/AuthenticateByName"
SEARCH_HINTS_URL = "/Search/Hints"
ARTISTS_URL = "/Artists"
PLAYLIST_URL = "/Playlists"
ARTIST_INSTANT_MIX_URL = ARTISTS_URL + "/InstantMix"
SONG_FILE_URL = "/Audio"
DOWNLOAD_URL = "/Download"
FAVORITE_URL = "/FavoriteItems"
ITEMS_ARTIST_KEY = "ArtistIds"
ITEMS_PARENT_ID_KEY = "ParentId"
ITEMS_GENRE_KEY =  "GenreIds="
ITEMS_FAVORITE_KEY = "IsFavorite=true"
ITEMS_URL = "/Items"
ITEMS_BY_FAVORITE_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=Audio&Recursive=true&" + ITEMS_FAVORITE_KEY
ITEMS_ALBUMS_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=MusicAlbum&Recursive=true&" + ITEMS_ARTIST_KEY + "="
ITEMS_SONGS_BY_ARTIST_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=Audio&Recursive=true&" + ITEMS_ARTIST_KEY + "="
ITEMS_SONGS_BY_GENRE_URL = ITEMS_URL + "?SortBy=SortName&SortOrder=Ascending&IncludeItemTypes=Audio&Recursive=true&" + ITEMS_GENRE_KEY
ITEMS_SONGS_BY_ALBUM_URL = ITEMS_URL + "?SortBy=IndexNumber&" + ITEMS_PARENT_ID_KEY + "="
LIMIT = "&Limit="
SERVER_INFO_URL = "/System/Info"
SERVER_INFO_PUBLIC_URL = SERVER_INFO_URL + "/Public"
# auth constants
AUTH_USERNAME_KEY = "username"
AUTH_PASSWORD_KEY = "Pw"
MAX_STREAM_BITRATE = "MaxStreamingBitrate=140000000&"
AUDIO_CODEC = "audioCodec=mp3&"
STATIC = "static=true&"
TRANSCODING_SETTING = "TranscodingContainer=ts&TranscodingProtocol=hls&"
#CONTAINER = "Container=opus%2Cmp3%7Cmp3%2Caac%2Cm4a%2Cm4b%7Caac%2Cflac%2Cwebma%2Cwebm%2Cwav%2Cogg&"
CONTAINER = "Container=mp3&"
#JELLY_ARGS = CONTAINER + TRANSCODING_SETTING + MAX_STREAM_BITRATE + AUDIO_CODEC
JELLY_ARGS = TRANSCODING_SETTING



# query param constants
AUDIO_STREAM = "stream.mp3"


class PublicJellyfinClient(object):
    """
    Handles the publically exposed jellyfin endpoints

    """

    def __init__(self, host, device="noDevice", client="NoClient", client_id="1234", version="0.1"):
        """
        Sets up the connection to the Jellyfin server
        :param host:
        """
        self.log = logging.getLogger(__name__)
        self.host = host
        self.auth = None
        self.device = device
        self.client = client
        self.client_id = client_id
        self.version = version

    def get_server_info_public(self):
        return requests.get(self.host + SERVER_INFO_PUBLIC_URL)


class JellyfinClient(PublicJellyfinClient):
    """
    Handles communication to the Jellyfin server

    """

    def __init__(self, host, username, password, device="noDevice", client="NoClient", client_id="1234", version="0.1"):
        """
        Sets up the connection to the Jellyfin server
        :param host:
        :param username:
        :param password:
        """

        super().__init__(host, device, client, client_id, version)
        self.log = logging.getLogger(__name__)
        self.auth = self._auth_by_user(username, password)

    def _auth_by_user(self, username, password):
        """
        Authenticates to jellyfin via username and password

        :param username:
        :param password:
        :return:
        """
        auth_payload = \
            {AUTH_USERNAME_KEY: username, AUTH_PASSWORD_KEY: password}
        response = self._post(AUTHENTICATE_BY_NAME_URL, auth_payload)
        assert response.status_code is 200
        return JellyfinAuthorization.from_response(response)

    def get_headers(self):
        """
        Returns specific Jellyfin headers including auth token if available

        :return:
        """
        media_browser_header = "MediaBrowser Client="+self.client +\
                               ", Device="+self.device +\
                               ", DeviceId="+self.client_id +\
                               ", Version="+self.version
        
        if self.auth and self.auth.user_id:
            media_browser_header = \
                media_browser_header + ", UserId=" + self.auth.user_id
        headers = {"X-Emby-Authorization": media_browser_header} 
        if self.auth and self.auth.token:
            headers["X-Emby-Token"] = self.auth.token
        return headers

    def search(self, query, media_types=[]):

        query_params = '?searchTerm={0}'.format(query)
        types = None
        for type in media_types:   
            types = type + ","

        if types:
            types = types[:len(types) - 1]
            query_params = query_params + '&IncludeItemTypes={0}'.format(types)

        self.log.debug(SEARCH_HINTS_URL + query_params)
        return self._get(SEARCH_HINTS_URL + query_params)

    def instant_mix(self, item_id):
        # userId query param is required even though its not
        # required in swagger
        # https://emby.media/community/index.php?/
        # topic/50760-instant-mix-api-value-cannot-be-null-error/
        instant_item_mix = '/Items/{0}/InstantMix?Limit=200'\
            .format(item_id)
        return self._get(instant_item_mix)

    def get_song_file(self, song_id):
        #Include song id again at the end, used to get track meta data with track_info()
        url = '{0}{1}/{2}/{3}?{4}DeviceId=none&song_id={5}'\
            .format(self.host, SONG_FILE_URL,
                    song_id, AUDIO_STREAM,JELLY_ARGS,song_id)
        self.log.debug("SONG URL: " + url)
        return url

    def get_album_art(self, album_id, tag_id, width, height, quality=95):
        # format: 
        url = '{0}/Items/{album_id}/Images/Primary?fillHeight={heigh}&fillWidth={width}&quality={quality}&tag={tag_id}'\
            .format(self.host, album_id=album_id, heigh=height, width=width, quality=quality, tag_id=tag_id)
        self.log.debug("SONG URL: " + url)
        return url

    def add_to_playlist(self, song_id, playlist_id):
        song = "&ids=" + song_id
        url = PLAYLIST_URL + "/" + str(playlist_id) + ITEMS_URL + "?userId=" + self.auth.user_id + song
        response = self._post(url, self.get_headers())
        if response.status_code == 204:
            return True
        else:
            return False

    # Create a new jellyfin playlist
    def create_playlist(self, name):
        payload = {'Name': name}
        payload.update(self.get_headers())
        url = PLAYLIST_URL + "?userId=" + self.auth.user_id
        response = self._post(url, payload)
        if response.status_code == 200:
            return True
        else:
            return False

    # Marks a song as a favorite
    def favorite(self, song_id):
        url = "/Users/" + self.auth.user_id + FAVORITE_URL + "/" + song_id
        response = self._post(url, self.get_headers())
        if response.status_code == 200:
            return True
        else:
            return False
    
    # Gets favorite songs
    def get_favorites(self):
        url = "/Users/" + self.auth.user_id + ITEMS_BY_FAVORITE_URL
        return self._get(url)

    def get_albums_by_artist(self, artist_id):
        url = "/Users/" + self.auth.user_id + ITEMS_ALBUMS_URL + str(artist_id)
        return self._get(url)

    def get_songs_by_album(self, album_id):
        url = "/Users/" + self.auth.user_id + ITEMS_SONGS_BY_ALBUM_URL + str(album_id)
        return self._get(url)

    def get_songs_by_artist(self, artist_id, limit=None):
        url = "/Users/" + self.auth.user_id + ITEMS_SONGS_BY_ARTIST_URL + str(artist_id)
        if limit:
            url = url + LIMIT+str(limit)
        return self._get(url)

    def get_songs_by_genre(self, genre_id, limit=None):
        url = "/Users/" + self.auth.user_id + ITEMS_SONGS_BY_GENRE_URL+ str(genre_id)
        if limit:
            url = url + LIMIT+str(limit)
        return self._get(url)

    def get_songs_by_playlist(self, playlist_id):
        url = PLAYLIST_URL + "/" + str(playlist_id) + ITEMS_URL + "?userId=" + self.auth.user_id
        return self._get(url)

    # Get item from id
    def get_item(self, song_id):
        url = "/Users/" + self.auth.user_id + ITEMS_URL + "?ids=" + str(song_id)
        return self._get(url)

    def get_all_artists(self):
        return self._get(ARTISTS_URL)

    def get_server_info(self):
        return self._get(SERVER_INFO_URL)

    def _post(self, url, payload):
        """
        Post with host and headers provided

        :param url:
        :param payload:
        :return:
        """
        return requests.post(
            self.host + url, json=payload, headers=self.get_headers())

    def _get(self, url):
        """
        Get with host and headers provided

        :param url:
        :return:
        """
        return requests.get(self.host + url, headers=self.get_headers())


class JellyfinAuthorization(object):

    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token

    @classmethod
    def from_response(cls, response):
        """
        Helper method for converting a response into
        an Jellyfin Authorization

        :param response:
        :return:
        """
        auth_content = response.json()
        return JellyfinAuthorization(
            auth_content["User"]["Id"], auth_content["AccessToken"])


class JellyfinMediaItem(object):

    """
    Stripped down representation of a media item in Jellyfin

    """

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type

    @classmethod
    def from_item(cls, item):
        media_item_type = MediaItemType.from_string(item["Type"])
        return JellyfinMediaItem(item["Id"], item["Name"], media_item_type)

    @staticmethod
    def from_list(items):
        media_items = []
        for item in items:
            media_items.append(JellyfinMediaItem.from_item(item))
        return media_items


class MediaItemType(Enum):
    ARTIST = "MusicArtist"
    ALBUM = "MusicAlbum"
    SONG = "Audio"
    OTHER = "Other"
    PLAYLIST = "Playlist"
    GENRE = "MusicGenre"

    @staticmethod
    def from_string(enum_string):
        for item_type in MediaItemType:
            if item_type.value == enum_string:
                return item_type
        return MediaItemType.OTHER

class JellyfinItemMetadata:
    """ 
    Stripped down representation of a media item in Jellyfin
    """

    def __init__(self, id, name, album, aritst, 
        year, thumbnail_url, background_url, location_type, media_type, uri):
        self.id = id
        self.name = name
        self.album = album
        self.artist = aritst
        self.year = year
        self.thumbnail_url = thumbnail_url
        self.background_url = background_url
        self.location_type = location_type
        self.media_type = media_type
        self.uri = uri


    @staticmethod    
    def from_json(json, client: JellyfinClient):
        """
        Helper method for converting a response into the `JellyfinItemMetadata` object
        :param json:
            Given the following sample json:
            {
                "Name": "TrackName",
                "ServerId": "guid",
                "Id": "guid",
                "ProductionYear": 1995,
                "IndexNumber": 1,
                "IsFolder": false,
                "Type": "Audio",
                "Artists": [
                    "Artist1"
                ],
                "ArtistItems": [
                    {
                    "Name": "Artist1",
                    "Id": "guid"
                    }
                ],
                "Album": "Album1",
                "AlbumId": "guid",
                "AlbumPrimaryImageTag": "guid",
                "AlbumArtist": "Artist1",
                "AlbumArtists": [
                    {
                    "Name": "Artist1",
                    "Id": "guid"
                    }
                ],
                "ImageTags": {},
                "BackdropImageTags": [],
                "ImageBlurHashes": {
                    "Primary": {
                    "guid": "base64"
                    }
                },
                "LocationType": "FileSystem",
                "MediaType": "Audio"
            }
        :return:
        """
        album_id = json["AlbumId"]
        tag_id = json["AlbumPrimaryImageTag"]
        return JellyfinItemMetadata(json["Id"], json["Name"],  json["Album"], json["AlbumArtist"],  
            json["ProductionYear"], client.get_album_art(album_id, tag_id, 128, 128, 95), 
            client.get_album_art(album_id, tag_id, 1024, 1024, 50), json["LocationType"], json["MediaType"],
            client.get_song_file(json["Id"]))

    def __str__(self):
        return f"{self.id}: {self.name} - {self.artist} - {self.album} - {self.year}: {self.thumbnail_url}"