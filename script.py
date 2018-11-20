import json
from lxml import html
import mutagen
from mutagen.easyid3 import EasyID3
import os
import re
import requests
import sys
from time import sleep

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

# break the data apart
released = [False if x == 'true' else True for x in re.findall(r'"unreleased_track":(true|false)', script)]
artist = re.findall(r'artist: "(.*?)"', script)[0].replace('\\', '').replace('/', '')
titles = [t.replace('\\', '').replace('/', '') for t in re.findall(r'"title":"(.*?)",', script)]
album_title = titles.pop(0) # the album title is the first item in the titles list
titles = titles[0:len(released)] # trim the titles list to just the album tracks
year = re.findall(r'album_release_date: "[0-9]{2} [a-zA-Z]{3} ([0-9]{4}?)', script)
urls = re.findall(r'https://t4.bcbits.com/stream/[a-z0-9]*/mp3-128/[0-9]*\?p=0&ts=[0-9]*&t=[a-z0-9]*&token=[0-9]*_[a-z0-9]*', script)

prep = 'Preparing to download '+str(album_title)+' by '+str(artist)+'...'
print(prep+'\n'+('-'*len(prep)))

# make a new directory for the album
directory = './downloads/'+artist+'/'+album_title+'/'
if not os.path.exists(directory):
    os.makedirs(directory)
else:
	if os.listdir(directory):
		print('Album already downloaded.')
		exit()

# download album cover
album_cover = requests.get(str(html.xpath('//link[@rel="image_src"]/@href')).strip('[]\''))
print('Downloading album artwork...')
with open(directory+"cover.jpg", 'wb') as jpg:
    jpg.write(album_cover.content)

# download and tag tracks
for x in range(len(titles)):
    if released[x]:
        sys.stdout.write('Downloading "'+titles[x]+'"...')
        sys.stdout.flush()

        try:
            with open(directory+str(x+1).zfill(2)+" "+titles[x]+".mp3", 'wb') as mp3:
                mp3.write(requests.get(urls[0]).content)
        except IndexError:
            print(' ERROR.\n"'+titles[x]+'" is a bonus or hidden track. Please download the album from Bandcamp directly to access this track.')
            os.remove(directory+str(x+1).zfill(2)+" "+titles[x]+".mp3")

        try:
            audio = EasyID3(directory+str(x+1).zfill(2)+" "+titles[x]+".mp3")
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(directory+str(x+1).zfill(2)+" "+titles[x]+".mp3", easy=True)
            audio.add_tags()
        except mutagen.MutagenError:
            continue

        audio['title'] = titles[x]
        audio['album'] = album_title
        audio['artist'] = artist
        audio['tracknumber'] = str(x+1)
        audio['date'] = year
        audio.save(v2_version=3)

        print(' tagged.')
        
        urls.pop(0)
        sleep(1)

print('-'*len(prep))
print('Download complete.')