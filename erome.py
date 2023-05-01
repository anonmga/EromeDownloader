import argparse
import os
from multiprocessing import Pool
from urllib.parse import urlsplit, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

_USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0'}

class Downloader():
    def __init__(self) -> None:
        _request = requests.get('https://www.erome.com')
        if _request.status_code != 200:
            raise ValueError("Could not access website. Please check if the website is online.")
        laravel_session = _request.cookies.get('laravel_session')
        xsrf_token = _request.cookies.get('XSRF-TOKEN')
        self.cookies = {'Cookies': f'XSRF-TOKEN="{xsrf_token}"; laravel_session="{laravel_session}"'}

    @classmethod
    def _download(cls, link, path, album_url):
        filename = os.path.splitext(os.path.basename(urlsplit(link).path))[0] + os.path.splitext(os.path.basename(urlsplit(link).path))[1]
        response = requests.get(link, stream=True, headers={'Referer': album_url})
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True, desc=filename)
        with open(os.path.join(path, filename), "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    progress_bar.update(len(chunk))
                    f.write(chunk)
        progress_bar.close()

    def download(self, album_url: str, path=None):
        parsed_url = urlparse(album_url)
        if parsed_url.netloc != 'www.erome.com':
            raise ValueError('The album URL must be from www.erome.com')
            
        _request = requests.get(f'{album_url}', cookies=self.cookies, headers=_USER_AGENT)
        _soup = BeautifulSoup(_request.text, 'html.parser')
        if _request.status_code == 404:
            return print(f"{album_url} - {_soup.find('div', {'class': 'col-md-12'}).h1.text}")

        links = []
        album_id = urlparse(album_url).path.split('/')[2]
        image_links = {image["data-src"] for image in _soup.find_all("img", {"class": "img-back"})}
        links.extend(image_links)
        video_links = {video_source["src"] for video_source in _soup.find_all("source")}
        links.extend(video_links)

        ## Makedir
        if path is None:
            os.makedirs(album_id, exist_ok=True)
            path = album_id

        with Pool(processes=4) as pool:
           pool.starmap(self._download, [(link, path, album_url) for link in links])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download images and videos from Erome albums.')
    parser.add_argument('album_url', type=str, nargs='?', help='URL of the Erome album to download')
    parser.add_argument('-p', '--path', type=str, help='Path to download the files to')
    parser.add_argument('--txt', type=str, help='Path to a text file containing Erome album URLs, one URL per line')
    args = parser.parse_args()
    downloader = Downloader()
    if args.txt:
        with open(args.txt, 'r') as f:
            for url in f:
                downloader.download(url.strip(), args.path)
    else:
        downloader.download(args.album_url, args.path)