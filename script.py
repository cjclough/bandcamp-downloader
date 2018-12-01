"""
    /brief A simple script for downloading albums on Bandcamp.
"""
import json
import os
import re
import sys
import mutagen
import requests

from lxml import html
from PyQt5.QtWidgets import QApplication   
from mutagen.easyid3 import EasyID3


def sanitize(data):
    return re.sub(r'[\\/:"*?<>|]+', '', data)

# get the album link
if len(sys.argv) < 2:
    url = input('Enter link to album: ')
    print()
else:
    url = str(sys.argv[1])

# request the page
page = requests.get(url)

# save the html
html = html.fromstring(page.text)

# isolate the <script> tag with necessary data
script = str(html.xpath('//script[contains(., "var TralbumData =")]/text()'))

# extract and validate the JSON data
j = re.findall(r'current: {.*artist: ".*?"', script)[0]
j = '{' + j.replace('\\n', '').replace('    ', '').replace('\\', '').replace('\\\\"', '\\"') + '}'
j = re.sub(r'packages: \[.*\],', '', j)
j = re.sub(r'url: ".*?,', '', j)
j = re.sub(r'({|,)([a-zA-Z_^true^false]*?):', r'\1"\2":', j)
data = json.loads(j)

prep = 'Preparing to download '+data['current']['title'].replace('\\', '')+' by '+data['artist'].replace('\\', '')+'...'
print(prep+'\n'+('-'*len(prep)))

# make a new directory for the album
directory = './downloads/'+sanitize(data['artist'])+'/'+sanitize(data['current']['title'])+'/'
if not os.path.exists(directory):
    os.makedirs(directory)
else:
    if os.listdir(directory):
        print('Album already downloaded.')
        exit()

# download album cover
album_cover = requests.get(
    str(html.xpath('//link[@rel="image_src"]/@href')).strip('[]\'')
    )
    
print('Downloading album artwork...')
with open(directory+"cover.jpg", 'wb') as jpg:
    jpg.write(album_cover.content)

for track in data['trackinfo']:
    if not track['unreleased_track']:
        file_name = sanitize(
            str(track['track_num']).zfill(2)+" "+track['title']+".mp3"
            )

        sys.stdout.write('Downloading "'+track['title'].replace('\\', '')+'"...')
        sys.stdout.flush()

        with open(directory+file_name, 'wb') as mp3:
            mp3.write(requests.get(track['file']['mp3-128']).content)

        try:
            audio = EasyID3(directory+file_name)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(directory+file_name, easy=True)
            audio.add_tags()
        except mutagen.MutagenError:
            continue

        audio['title'] = track['title'].replace('\\', '')
        audio['album'] = data['current']['title'].replace('\\', '')
        audio['artist'] = data['artist'].replace('\\', '')
        audio['tracknumber'] = str(track['track_num'])
        audio['date'] = data['album_release_date'][7:11]
        audio.save(v2_version=3)

        print(' tagged.')

print('-'*len(prep))
print('Download complete.')
