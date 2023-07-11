import hashlib
from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, ocp_search
from ovos_utils.parse import fuzzy_match
from ovos_utils.parse import match_one
from ovos_workshop.decorators import intent_handler, adds_context, removes_context
from ovos_audio.audio import AudioService
from ovos_backend_client.api import DeviceApi
from ovos_utils import classproperty
from random import shuffle
from .jellyfin_croft import JellyfinCroft, IntentType
from os.path import join, dirname


class JellyfinSkill(OVOSCommonPlaybackSkill):

    def __init__(self):
        super(JellyfinSkill, self).__init__("Jellyfin")
        self.supported_media = [MediaType.GENERIC, MediaType.AUDIO, MediaType.MUSIC, MediaType.AUDIOBOOK, MediaType.VIDEO, MediaType.MOVIE, MediaType.CARTOON]
        self.skill_icon = join(dirname(__file__), "ui", "Jellyfin.png")

        self._setup = False
        self.audio_service = None
        self.jellyfin_croft = None
        # TODO: instance-level songs list should no longer be assigned
        self.songs = []
        self.device_id = hashlib.md5(
            ('Jellyfin'+DeviceApi().identity.uuid).encode())\
            .hexdigest()

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=True,
                                   network_before_load=True,
                                   gui_before_load=False,
                                   requires_internet=True,
                                   requires_network=True,
                                   requires_gui=False,
                                   no_internet_fallback=False,
                                   no_network_fallback=False,
                                   no_gui_fallback=True)

    def initialize(self):
        # self.log.debug(f"self.config={self.config}")
        pass

    def connect_to_jellyfin(self, diagnostic=False):
        """
        Attempts to connect to the server based on the config
        if diagnostic is False an attempt to auth is also made
        returns true/false on success/failure respectively

        :return:
        """
        auth_success = False
        if not "hostname" in  self.settings or not "username" in self.settings or not "password" in self.settings:
            self.speak_dialog("configuration_fail")
            return False

        self.log.debug("Testing connection to: " + self.settings["hostname"])
        try:
            self.jellyfin_croft = JellyfinCroft(
                self.settings["hostname"] + ":" + str(self.settings["port"]),
                self.settings["username"], self.settings["password"],
                self.device_id, diagnostic)
            auth_success = True
        except Exception as e:
            self.log.info("failed to connect to jellyfin, error: {0}".format(str(e)))

        return auth_success

    def _search_jellyfin(self, message: str, media_type: MediaType=MediaType.GENERIC, intent_type: IntentType=IntentType.from_string('media')):
        # first thing is connect to jellyfin or bail
        if not self.connect_to_jellyfin():
            self.speak_dialog('configuration_fail')
            return

         # match the request media_type
        base_score = 0
        if media_type == MediaType.MUSIC :
            base_score += 10
        # else:
        #     base_score -= 15  # some penalty for proof of concept

        explicit_request = False
        if self.voc_match(message, "jellyfin"):
            # explicitly requested our skill
            base_score += 50
            message = self.remove_voc(message, "jellyfin")  # clean up search str
            explicit_request = True
            self.extend_timeout(1)

        return self.jellyfin_croft.handle_intent(message, intent_type), base_score


    # common play
    @ocp_search()
    def search_jellyfin_artist(self, message: str, media_type: MediaType=None):

        songs, base_score = self._search_jellyfin(message, media_type, IntentType.from_string('artist'))
        self.log.info(f"got base_score {base_score} for {len(songs)} songs")

        if not songs:
            return []

        pl = [{
                "match_confidence": 100-idx,
                "media_type": MediaType.MUSIC,
                # "length": entry.length * 1000 if entry.length else 0,
                "title": v.name,
                "album": v.album,
                "artist": v.artist,
                "uri": v.uri, 
                "playback": PlaybackType.AUDIO_SERVICE,
                "image": v.thumbnail_url,
                "bg_image": v.background_url,
                "skill_icon": self.skill_icon,
                "skill_id": self.skill_id
            } for idx, v in enumerate(songs)]

        name = songs[0].artist
        score = (fuzzy_match(name, message) * 100) + base_score

        self.log.info(f"artist '{name}' with score: {score}")
        ret = {
                    "match_confidence": score,
                    "media_type": MediaType.AUDIO,
                    "playback": PlaybackType.AUDIO_SERVICE,
                    "playlist": pl,  # return full playlist result
                    "image": songs[0].thumbnail_url,
                    "bg_image": songs[0].background_url,
                    "skill_icon": self.skill_icon,
                    "album": songs[0].album,
                    ##"duration": sum(t["duration"] for t in pl),
                    "title": songs[0].album + f" ({songs[0].artist}|Full Album)",
                    "skill_id": self.skill_id
                }
        self.log.debug(ret)
        return [ret]
        

    @ocp_search()
    def search_jellyfin_tracks(self, message: str, media_type: MediaType=None):

        songs, base_score = self._search_jellyfin(message, media_type, IntentType.from_string('media'))

        # self.log.debug(songs)
       
        for v in songs:
            name = v.name
            score = (fuzzy_match(name, message) * 100) + base_score
            yield {
                    "match_confidence": score,
                    "media_type": MediaType.MUSIC,
                    "title": v.name,
                    "album": v.album,
                    "artist": v.artist,
                    # "length": entry.length * 1000 if entry.length else 0,
                    "uri": v.uri, 
                    "playback": PlaybackType.AUDIO_SERVICE,
                    "image": v.thumbnail_url,
                    "bg_image": v.background_url,
                    "skill_icon": self.skill_icon,
                    "skill_id": self.skill_id
                }


    # Play favorites
    @intent_handler('isfavorite.intent')
    def handle_is_favorite(self, message):
        self.log.info(message.data)
        if not self.connect_to_jellyfin():
            self.speak_dialog('configuration_fail')
            return
        self.songs = self.jellyfin_croft.get_favorites()
        if not self.songs or len(self.songs) < 1:
            self.log.info('No songs Returned')
            self.speak_dialog('play_fail', {"media": "favorites"})
        else:
            # setup audio service and play        
            self.audio_service = AudioService(self.bus)
            backends = self.audio_service.available_backends()
            self.log.debug("BACKENDS. VLC Recommended")
            for key , value in backends.items():
                self.log.debug(str(key) + " : " + str(value))
            self.speak_dialog('isfavorite')
            self.audio_service.play(self.songs, message.data['utterance'])

    @intent_handler('shuffle.intent')
    def handle_shuffle(self, message):
        self.log.info(message.data)
        # Back up meta data
        track_meta = self.jellyfin_croft.get_all_meta()
        # first thing is connect to jellyfin or bail
        if not self.connect_to_jellyfin():
            self.speak_dialog('configuration_fail')
            return

        if not self.songs or len(self.songs) < 1:
            self.log.info('No songs Returned')
            self.speak_dialog('shuffle_fail')
        else:
            self.log.info(track_meta)
            # setup audio service and, suffle play
            shuffle(self.songs)
            self.audio_service = AudioService(self.bus)
            self.speak_dialog('shuffle')
            self.audio_service.play(self.songs, message.data['utterance'])
            # Restore meta data
            self.jellyfin_croft.set_meta(track_meta)

    def speak_playing(self, media):
        data = dict()
        data['media'] = media
        self.speak_dialog('jellyfin', data)

    @intent_handler('playingsong.intent')
    def handle_playing(self, message):
        track = "Unknown"
        artist = "Unknown"
        if self.audio_service.is_playing:
            # See if I can get the current track index instead
            track = self.audio_service.track_info()['name']
            artist = self.audio_service.track_info()['artists']
            if artist != [None]:
                self.speak_dialog('whatsplaying', {'track' : track, 'artist': artist})
            else:
                track = self.jellyfin_croft.get_meta(self.audio_service.track_info()['name'])
                if track != False:
                    self.speak_dialog('whatsplaying', {'track' : track['Name'], 'artist': track['Artists']})
                else:
                    self.speak_dialog('notrackinfo')
        else:
            self.speak_dialog('notplaying')

    @intent_handler('playlist.intent')
    def handle_playlist_add(self, message):
        if self.audio_service.is_playing:
            track = self.audio_service.track_info()['name']
            track_name = self.jellyfin_croft.get_meta(track)
            add_to = self.jellyfin_croft.add_to_playlist(track, message.data.get('playlist_name'))
            if add_to == True:
                self.speak_dialog('playlist', {'media' : track_name['Name'], 'playlist_name' : message.data.get('playlist_name')})
                return
        self.speak_dialog('playlist_fail', {'media' : track_name['Name'], 'playlist_name' : message.data.get('playlist_name')})
        return

    # Intent for creating a new playlist
    @intent_handler('createplaylist.intent')
    def handle_create_playlist(self, message):
        if not self.connect_to_jellyfin():
            return None
        confirm = self.ask_yesno('playlistnameconfirm', {'playlist_name' : message.data.get('playlist_name')})
        if confirm == 'yes':
            create_new = self.jellyfin_croft.create_playlist(message.data.get('playlist_name'))
            if create_new == True:
                self.speak_dialog('createplaylist', {'playlist_name' : message.data.get('playlist_name')})
                return
        else:
            return
        self.speak_dialog('createplaylist_fail', {'playlist_name' : message.data.get('playlist_name')})
        return

    # Intent foor marking a song as favorite
    @intent_handler('favorite.intent')
    def handle_favorite(self, message):
        if self.audio_service.is_playing:
            track = self.audio_service.track_info()['name']
            track_name = self.jellyfin_croft.get_meta(track)
            favorite = self.jellyfin_croft.favorite(track)
            if favorite == True:
                self.speak_dialog('favorite', {'track_name' : track_name['Name']})
                return
            else:
                self.speak_dialog('favorite_fail', {'track_name' : track_name['Name']})
                return

    @intent_handler('diagnostic.intent')
    def handle_diagnostic(self, message):

        self.log.info(message.data)
        self.speak_dialog('diag_start')

        # connect to jellyfin for diagnostics
        self.connect_to_jellyfin(diagnostic=True)
        connection_success, info = self.jellyfin_croft.diag_public_server_info()

        if connection_success:
            self.speak_dialog('diag_public_info_success', info)
        else:
            self.speak_dialog('diag_public_info_fail', {'host': self.settings['hostname']})
            self.speak_dialog('general_check_settings_logs')
            self.speak_dialog('diag_stop')
            return

        if not self.connect_to_jellyfin():
            self.speak_dialog('diag_auth_fail')
            self.speak_dialog('diag_stop')
            return
        else:
            self.speak_dialog('diag_auth_success')

        self.speak_dialog('diagnostic')

    def stop(self):
        pass


def create_skill():
    return JellyfinSkill()
