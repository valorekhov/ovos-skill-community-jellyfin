from skill_ovos_jellyfin.media_item_type import MediaItemType

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