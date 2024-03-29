import shutil
from pathlib import Path

import requests

from pydriverr.custom_logger import logger
from pydriverr.support import Support


class Downloader:
    """Helper class to download URLs"""

    def __init__(self):
        self._session = requests.Session()
        self._support = Support()

    def get_url(self, url: str, stream=False) -> requests.Response:
        """
        Download any URL and return `requests` object.

        :param url: URL for the get request
        :param stream: Should the response content be retrieved when accessed. Use while downloading driver files
                       (default: True)
        :return: Whole request `Response` object
        """
        logger.debug(f"Downloading: {url}")
        try:
            r = self._session.get(url, stream=stream)
            if r.status_code == 200:
                return r
            else:
                self._support.exit(f"Cannot download file {url}")
        except requests.exceptions.ConnectTimeout:
            self._support.exit("Connection error")

    def dl_driver(self, url: str, dst: Path) -> None:
        """
        Download WebDriver archive to given path.

        :param url: URL of the WebDriver
        :param dst: Path where to save WebDriver
        :return: None
        """
        logger.debug(f"Downloading from: {url} to: {dst}")
        with open(str(dst), "wb") as f:
            r = self.get_url(url, stream=True)
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
