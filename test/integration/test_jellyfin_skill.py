from skill_ovos_jellyfin.jellyfin_client import JellyfinClient, MediaItemType, JellyfinMediaItem
from skill_ovos_jellyfin.jellyfin_croft import JellyfinCroft
from skill_ovos_jellyfin import JellyfinSkill 
from test.integration import HOST, PASSWORD, USERNAME

class TestJellyfinSkill(object):

    def test_ocp_search_artist(self):
        artist = 'yalla'

        skill = JellyfinSkill()
        skill.settings = {
            'hostname': HOST,
            'username': USERNAME,
            'password': PASSWORD
        }

        assert list(skill.search_jellyfin_artist(artist))

        assert list(skill.search_jellyfin_tracks(artist))

        assert list(skill.featured_media())
