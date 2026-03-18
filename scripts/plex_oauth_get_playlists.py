#!/usr/bin/env python3
"""
Run this script to start a Plex OAuth PIN login flow.
It prints a PIN and waits for you to sign in with it at https://plex.tv/link.
After successful login lists all users and their music playlists.
"""

from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
import sys
import time
from plexapi.server import PlexServer


def main():
    pinlogin = MyPlexPinLogin(oauth=False)

    print('\nOpen https://plex.tv/link in your browser and enter this 4-character PIN:')
    try:
        # Accessing .pin will create the PIN if needed
        code = pinlogin.pin
        print('PIN:', code)
    except Exception as e:
        print('Failed to get PIN:', e)
        sys.exit(1)

    print('Waiting up to 300s for you to complete login...')
    # poll checkLogin() up to 300 seconds with debug output
    ok = False
    for i in range(300):
        try:
            if pinlogin.checkLogin():
                print(f'PIN login succeeded after {i} seconds')
                ok = True
                break
        except Exception as e:
            print('checkLogin() raised:', repr(e))
        if getattr(pinlogin, 'expired', False):
            print('PIN expired')
            break
        time.sleep(1)
    if not ok:
        print('Login timed out or was not completed.')
        sys.exit(1)

    token = getattr(pinlogin, 'token', None)

    acc = MyPlexAccount(token=token)

    # Get Base URL for the local connection
    try:
        res = acc.resources()
        server_res = None
        for r in res:
            provides = getattr(r, 'provides', '') or ''
            if 'server' in provides:
                server_res = r
                break
        if server_res:
            conns = getattr(server_res, 'connections', []) or []
            local_conn = next((c for c in conns if getattr(c, 'local', False)), None)
            if local_conn:               
                baseurl = getattr(local_conn, 'uri', None)
                if baseurl:
                    print('Local baseurl (from local_conn.uri):', baseurl)
                else:
                    print('local_conn.uri not found, cannot determine baseurl')
            else:
                print('No local connection found')
        else:
            print('No server resource found')
    except Exception as e:
        print('Error getting local baseurl:', e)

    # List Managed Users (Plex Home users)
    try:
        users = acc.users()
    except Exception as e:
        print('Failed to fetch users:', e)
        users = []

    # Filter for managed (restricted) users only
    managed_users = [u for u in users if getattr(u, 'restricted', None) in (True, 1, '1')]

    main_account_info = {
        'username': getattr(acc, 'username', None),
        'acc_obj': acc
    }

    print('\nUsername/Token pairs for all users:')
    user_token_pairs = []
    #  Insert the main account as the first entry
    user_token_pairs.append({'username': main_account_info['username'], 'token': token})
    # Managed users
    for u in managed_users:
        try:
            user_acc = acc.switchHomeUser(u)
            user_token_pairs.append({'username': u.username or u.title, 'token': user_acc.authToken})
        except Exception as e:
            print(f"Failed to get token for managed user {u.username or u.title}: {e}")
    for pair in user_token_pairs:
        print(f"{pair['username']}: {pair['token']}")

    plex_server = PlexServer(baseurl, token)

    # List audio playlists for the main account
    print(f"\n--- Audio Playlists for Main Account: {main_account_info['username']} ---")
    try:
        main_audio_playlists = [pl for pl in plex_server.playlists()
                               if getattr(pl, 'playlistType', None) == 'audio' and not getattr(pl, 'smart', False)]
        if main_audio_playlists:
            for playlist in main_audio_playlists:
                print(f"* {playlist.title} ({playlist.playlistType}, {playlist.leafCount} items)")
        else:
            print("No audio playlists found for main account.")
    except Exception as e:
        print(f"Could not retrieve playlists for main account: {e}")

    # List audio playlists for each managed user
    for user in managed_users:
        print(f"\n--- Audio Playlists for Managed User: {user.title} ---")
        try:
            user_plex_server = plex_server.switchUser(user)
            audio_playlists = [pl for pl in user_plex_server.playlists()
                               if getattr(pl, 'playlistType', None) == 'audio' and not getattr(pl, 'smart', False)]
            if audio_playlists:
                for playlist in audio_playlists:
                    print(f"* {playlist.title} ({playlist.playlistType}, {playlist.leafCount} items)")
            else:
                print(f"No audio playlists found for {user.title}.")
        except Exception as e:
            print(f"Could not retrieve playlists for {user.title}: {e}")

if __name__ == '__main__':
    main()
