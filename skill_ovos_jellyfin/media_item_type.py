from enum import Enum

class MediaItemType(Enum):
    ARTIST = "MusicArtist"
    ALBUM = "MusicAlbum"
    SONG = "Audio"
    OTHER = "Other"
    PLAYLIST = "Playlist"
    GENRE = "MusicGenre"

    def __str__(self):
        return self.value

    @staticmethod
    def from_string(enum_string):
        for item_type in MediaItemType:
            if item_type.value == enum_string:
                return item_type
        return MediaItemType.OTHER