from flask import Flask, request, render_template, session
import requests
import base64
import os
import csv
from dotenv import load_dotenv

load_dotenv('secrets.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize', methods =['POST'])
def authorize():
    session['playlist_id'] = request.form.get('playlist_id')
    # Get Spotify App client ID and secret
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')

    # Use Spotify's Client Credentials flow for authorization (https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow)
    credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('utf-8')
    url = 'https://accounts.spotify.com/api/token'
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    data = {
        'grant_type': 'client_credentials' 
    }
    
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        token = response.json().get('access_token')
        session['token'] = token
        print(token)
    else:
        print(response.status_code)
    return get_playlist()

@app.route('/get_playlist')
def get_playlist():
    playlist_id = session.get('playlist_id')

    # Use Spotify's Get Playlist Items API (https://developer.spotify.com/documentation/web-api/reference/get-playlists-tracks)
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {
        'Authorization': f'Bearer {session.get("token")}'
    }
    params = {
        'limit': 100,
        'offset': 0
    }

    response = requests.get(url, headers=headers).json()
    total = response.get('total')

    if not os.path.exists('output'):
        os.mkdir('output')

    with open(f'output/{playlist_id}.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Track Name', 'Track Duration', 'Artists', 'Album', 'Release Date', 'Spotify URL'])
        while True:
            response = requests.get(url, headers=headers, params=params).json()
            tracks = response['items']
            for track in tracks:
                print(f'{params["offset"]}/{total}')
                track = track.get('track')
                track_name = track.get('name') # Get track name
                track_duration_ms = track.get('duration_ms') # Get track duration in ms
                track_duration_m, track_duration_ms = divmod(track_duration_ms, 60000) # Convert track duration to minutes and seconds
                track_duration_s = track_duration_ms // 1000 # Convert track duration from milliseconds to seconds
                track_duration = f'{track_duration_m}:{track_duration_s:02}' # Unite the minute and second durations for easier reading
                track_album = track.get('album').get('name') # Get track album
                album_release = track.get('album').get('release_date') # Get album release date
                artist_count = len(track.get('artists')) # Get number of artists for the track
                track_artists = track.get('artists')[0].get('name') # Get the first artist so it's not blank for the artist iteration
                for i in range(1, artist_count): 
                    artist = track.get('artists')[i].get('name') # Get other artists (if there are any)
                    track_artists = f'{track_artists}, {artist}' # Add other artists to track_artists (if there are any)
                spotify_url = track.get('external_urls').get('spotify') # Get the Spotify URL for the track
                writer.writerow([track_name, track_duration, track_artists, track_album, album_release, spotify_url])

            if response['next']:
                # Spotify's API has a limit of 100 tracks per request, so increment the offset for next request
                params['offset'] += 100 
            else:
                break
    return f"output result to {playlist_id}.csv"
