from lastfm_mpris2_scrobbler.globals import get_unix_timestamp
from lastfm_mpris2_scrobbler.globals import logger

class PlayerState:
    def __init__(self, metadata_dict = None, playback_status = "Playing") -> None:
        self.total_played_time = 0
        self.last_observation_timestamp = get_unix_timestamp()
        self.trackid = ""
        self.title = ""
        self.artist = ""
        self.if_scrobbled = False
        self.is_length_dynamic = False
        self.length = 0
        if metadata_dict is not None:
            self.update_status(metadata_dict, playback_status, self.last_observation_timestamp)

    def set_value(self, trackid, artist, title, timestamp, album, album_artist, track_number, duration):
        self.trackid = trackid
        self.artist = artist
        self.title = title
        self.last_observation_timestamp = timestamp
        self.album = album
        self.albumArtist = album_artist
        self.trackNumber = track_number
        self.length = duration
        return self

    def handle_multiple_artists(self, artist_array):
        # convert artist array into a single string
        return ", ".join(artist_array)
    
    def update_status(self, metadata_dict, playback_status, timestamp):
        # 1. Read all metadata into local variables
        new_trackid = self.get_value_from_dict(metadata_dict, "mpris:trackid")
        raw_new_title = self.get_value_from_dict(metadata_dict, "xesam:title").strip()
        new_artist_list = self.get_value_from_dict(metadata_dict, "xesam:artist", expect_type="list")
        new_length_us = self.get_value_from_dict(metadata_dict, "mpris:length", expect_type="int")
        new_art_url = self.get_value_from_dict(metadata_dict, "mpris:artUrl")
        new_album = self.get_value_from_dict(metadata_dict, "xesam:album")
        new_album_artist_list = self.get_value_from_dict(metadata_dict, "xesam:albumArtist", expect_type="list")
        new_disc_number = self.get_value_from_dict(metadata_dict, "xesam:discNumber", expect_type="int")
        new_first_used = self.get_value_from_dict(metadata_dict, "xesam:firstUsed")
        new_track_number = self.get_value_from_dict(metadata_dict, "xesam:trackNumber", expect_type="int")
        new_url = self.get_value_from_dict(metadata_dict, "xesam:url")

        # 2. Determine definitive artist and title from new metadata
        final_new_artist = self.handle_multiple_artists(new_artist_list)
        final_new_title = raw_new_title

        is_stream = not new_artist_list
        if is_stream:
            try:
                # For streams, parse "Artist - Title" format
                artist_part, title_part = raw_new_title.split(" - ", 1)
                final_new_artist = artist_part.strip()
                final_new_title = title_part.strip()
            except ValueError:
                # If split fails, the whole raw title is the title
                final_new_title = raw_new_title

        # 3. Compare with stored state to see if song has changed
        if is_stream:
            # For streams, we can't trust trackid, compare artist and title
            is_same_song = (self.artist == final_new_artist and self.title == final_new_title)
        else:
            # For regular tracks, trackid is most reliable
            is_same_song = (self.trackid == new_trackid)

        # 4. Update played time and scrobble status
        if is_same_song:
            self.total_played_time += (timestamp - self.last_observation_timestamp) if playback_status == "Playing" else 0
        else:
            self.total_played_time = 0
            self.if_scrobbled = False
            self.is_length_dynamic = False

        # 5. Update dynamic length flag
        new_length = int(new_length_us / 1000000)
        if is_same_song and new_length > self.length:
            self.is_length_dynamic = True
            
        # 6. Update all self properties with the new, processed values
        self.length = new_length
        self.trackid = new_trackid
        self.title = final_new_title
        self.artist = final_new_artist
        
        self.artUrl = new_art_url
        self.album = new_album
        self.albumArtist = self.handle_multiple_artists(new_album_artist_list)
        if self.albumArtist == "":
            self.albumArtist = self.artist
        self.discNumber = new_disc_number
        self.firstUsed = new_first_used
        self.trackNumber = new_track_number
        self.url = new_url
        if self.url == "":
            self.url = "/"
            
        self.last_observation_timestamp = timestamp
        self.playback_status = playback_status

    def get_value_from_dict(self, data: dict, key: str, expect_type: str = "str"):
        try:
            value = data[key]
            if expect_type == "str":
                return str(value)
            elif expect_type == "int":
                return int(value)
            elif expect_type == "list":
                return value
            else:
                logger.exception(f"Unexpected {expect_type=}")
        except Exception as e:
            logger.debug(f"Failed to retrieve {key=} from player. Value for this key is set to default")
            if expect_type == "str":
                return ""
            elif expect_type == "int":
                return 1
            elif expect_type == "list":
                return []
            else:
                logger.exception(f"Unexpected {expect_type=}")
