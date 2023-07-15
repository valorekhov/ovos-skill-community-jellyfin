from typing import List
from skill_ovos_jellyfin.jellyfin_media_item import JellyfinMediaItem
from skill_ovos_jellyfin.media_item_type import MediaItemType

class JellyfinItemMetadata(JellyfinMediaItem):
    """ 
    Stripped down representation of a media item in Jellyfin
    """

    def __init__(self, id, name, album, aritst, 
        year, thumbnail_url, background_url, location_type, media_type, uri,
        duration:int|None, is_favorite=False, play_count = 0):

        super().__init__(id, name, MediaItemType.from_string(media_type))    

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
        self.duration = duration
        self.is_favorite = is_favorite
        self.play_count = play_count

    def __str__(self):
        return f"{self.id}: {self.name} - {self.artist} - {self.album} - {self.year}: {self.thumbnail_url}"

    @staticmethod    
    def from_json(json:dict, client):
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
        tag_id = json.get("AlbumPrimaryImageTag")
        user_data = json.get("UserData") or {}
        return JellyfinItemMetadata(json["Id"], json["Name"],  json.get("Album"), json.get("AlbumArtist"),  
            json.get("ProductionYear"), client.get_album_art(album_id, tag_id, 128, 128, 95) if tag_id else None, 
            client.get_album_art(album_id, tag_id, 1024, 1024, 50) if tag_id else None, json.get("LocationType"), json.get("MediaType"),
            client.get_song_file(json["Id"]), (json.get("RunTimeTicks") or 0) / 10000, user_data.get("IsFavorite"), user_data.get("PlayCount"))
    
    @staticmethod    
    def from_json_list(jsonList:List[dict], client):
        return [JellyfinItemMetadata.from_json(json, client) for json in jsonList]