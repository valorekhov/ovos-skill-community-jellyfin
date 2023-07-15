from enum import Enum

class IntentType(Enum):
    MEDIA = "media"
    ARTIST = "artist"
    ALBUM = "album"
    SONG = "song"
    PLAYLIST = "playlist"
    GENRE = "genre"
    VIDEO = "video"
    MOVIE = "movie"

    def __str__(self):
        return self.value

    @staticmethod
    def from_string(enum_string):
        assert enum_string is not None
        for item_type in IntentType:
            if item_type.value == enum_string.lower():
                return item_type
