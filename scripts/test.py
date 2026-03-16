from plexapi.server import PlexServer

# Configuration
TOKEN = "token"
BASEURL = "baseurl"
MANAGED_USER = "user"
PLAYLIST = "playlist"


# 1. Authenticate and Connect using PlexServer (baseurl + token)
plex_server = PlexServer(BASEURL, TOKEN)

# 2. Switch Context and Add Item
target_user = next(u for u in plex_server.myPlexAccount().users() if u.title == MANAGED_USER)
user_plex = plex_server.switchUser(target_user)

# Get the song with ratingKey 15684
song_item = user_plex.fetchItem('/library/metadata/15684')

playlists = user_plex.playlists()
playlist = None
for pl in playlists:
    if pl.title == PLAYLIST:
        playlist = pl
        break
if not playlist:
    try:
        playlist = user_plex.createPlaylist(PLAYLIST, items=[song_item])
        print(f'[PLEX] Created playlist "{PLAYLIST}" and added track', flush=True)
    except Exception as e:
        print(f"[PLEX] Error creating playlist: {str(e)}", flush=True)
else:
    playlist = user_plex.playlist(PLAYLIST)
    playlist.addItems([song_item])
    print(f'[PLEX] Added track to existing playlist "{PLAYLIST}"', flush=True)
