import sys
import json
import mutagen
import os
import re
import requests

from lxml import html
from mutagen.easyid3 import EasyID3
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QAction, QLineEdit, QTextEdit, QLabel
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSlot
from PyQt5.Qt import Qt
 

class BandcampDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'Bandcamp Downloader'
        self.left = 100
        self.top = 100
        self.width = 310
        self.height = 200
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setFixedSize(self.width, self.height)

        # album link/search box
        self.inputLine = QLineEdit(self)
        self.inputLine.move(5, 10)
        self.inputLine.resize(300,20)
        self.inputLine.setPlaceholderText("Enter link to album or search query")
        self.inputLine.textChanged.connect(self.enable_dlButton)

        # download button
        self.dlButton = QPushButton('Download', self)
        self.dlButton.move(235,35)
        self.dlButton.resize(70, 25)
        self.dlButton.setEnabled(False)
        self.dlButton.clicked.connect(self.on_download_clicked)

        # search button
        self.searchButton = QPushButton('Search', self)
        self.searchButton.move(160, 35)
        self.searchButton.resize(70, 25)
        self.searchButton.clicked.connect(self.on_search_clicked)

        # album data label
        self.albumData = QLabel('', self)
        self.albumData.move(135, 70)
        self.albumData.resize(170, 50)

        # current task label
        self.currentDownload = QLabel('', self)
        self.currentDownload.move(135, 125)
        self.currentDownload.resize(170, 50)
        self.currentDownload.setWordWrap(True)

        # album cover container
        self.albumContainer = QLabel(self)
        self.albumContainer.move(5, 70)
        self.albumContainer.resize(125,125)

        self.show()

    @pyqtSlot()
    def enable_dlButton(self):
        if re.search(r'https://.*?.com/album/.*?', self.inputLine.text()):
            self.dlButton.setEnabled(True)
        else:
            self.dlButton.setEnabled(False)
        QApplication.processEvents()

    @pyqtSlot()
    def on_search_clicked(self):
        if self.inputLine.text() == '' or re.search(r'https://.*?.com/album/.*?', self.inputLine.text()):
            return

        response = requests.get('https://bandcamp.com/search?q='+self.inputLine.text())
        page = html.fromstring(response.text)

        link = str(page.xpath('//ul[@class="result-items"]/li[@class="searchresult album"]/a[@class="artcont"]/@href')[0])
        link = link[0:link.find("?")]
        title = str(page.xpath('//ul[@class="result-items"]/li[@class="searchresult album"]/div[@class="result-info"]/div[@class="heading"]/a/text()')[0]).strip()
        artist = str(page.xpath('//ul[@class="result-items"]/li[@class="searchresult album"]/div[@class="result-info"]/div[@class="subhead"]/text()')[0]).strip()
        released = str(page.xpath('//ul[@class="result-items"]/li[@class="searchresult album"]/div[@class="result-info"]/div[@class="released"]/text()')[0]).strip()
        cover_preview = requests.get(str(page.xpath('//ul[@class="result-items"]/li[@class="searchresult album"]/a[@class="artcont"]/div[@class="art"]/img/@src')[0]))

        self.album = QPixmap('')
        self.album.loadFromData(cover_preview.content)
        self.albumContainer.setPixmap(self.album.scaled(125,125, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        self.albumContainer.resize(125,125)
        self.albumData.setText(title+'\n'+artist+'\n'+released)

        self.inputLine.setText(link)
        self.currentDownload.setText('')
        QApplication.processEvents()


    @pyqtSlot()
    def on_download_clicked(self):
        def sanitize(data):
            return re.sub(r'[\\/:"*?<>|]+', '', data)
        
        self.albumContainer.clear()
        self.albumData.clear()
        self.currentDownload.clear()

        # request the page
        response = requests.get(self.inputLine.text())

        # save the page
        page = html.fromstring(response.text)

        # isolate the <script> tag with necessary data
        script = str(page.xpath('//script[contains(., "var TralbumData =")]/text()'))

        # extract and validate the JSON data
        j = re.findall(r'current: {.*artist: ".*?"', script)[0]
        j = '{' + j.replace('\\n', '').replace('    ', '').replace('\\"', '').replace('\\', '').replace('\\\\"', '\\"') + '}'
        j = re.sub(r'packages: \[.*\],', '', j)
        j = re.sub(r'url: ".*?,', '', j)
        j = re.sub(r'({|,)([a-zA-Z_^true^false]*?):', r'\1"\2":', j)
        data = json.loads(j)

        # make a new directory for the album
        directory = './downloads/'+sanitize(data['artist'])+'/'+sanitize(data['current']['title'])+'/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        else:
            if os.listdir(directory):
                self.currentDownload.setText('Album already downloaded.')
                QApplication.processEvents()
                return

        # download album cover
        album_cover = requests.get(str(page.xpath('//link[@rel="image_src"]/@href')).strip('[]\''))
        with open(directory+"cover.jpg", 'wb') as jpg:
            jpg.write(album_cover.content)

        # update GUI with data
        self.album = QPixmap('')
        self.album.loadFromData(album_cover.content)
        self.albumContainer.setPixmap(self.album.scaled(125,125, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        self.albumData.setText(data['current']['title'].replace('\\', '')+'\n'+data['artist'].replace('\\', '')+'\n'+data['album_release_date'][7:11])
        QApplication.processEvents()

        for track in data['trackinfo']:
            if not track['unreleased_track']:
                file_name = sanitize(str(track['track_num']).zfill(2)+" "+track['title']+".mp3")

                self.currentDownload.setText('Downloading "'+track['title'].replace('\\', '')+'"...')
                QApplication.processEvents()

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

        self.currentDownload.setText('Download complete.')
        self.inputLine.setText('')
        self.dlButton.setEnabled(False)
        QApplication.processEvents()
