import logging
import shutil
from pathlib import Path

import requests

from pydriver.support import Support


class Downloader:
    """Helper class to download URLs"""

    def __init__(self):
        self._logger = logging.getLogger("PyDriver")
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
        self._logger.debug(f"Downloading: {url}")
        r = self._session.get(url, stream=stream)
        if r.status_code == 200:
            return r
        else:
            self._support.exit(f"Cannot download file {url}")

    def dl_driver(self, url: str, dst: Path) -> None:
        """
        Download WebDriver archive to given path.

        :param url: URL of the WebDriver
        :param dst: Path where to save WebDriver
        :return: None
        """
        self._logger.debug(f"Downloading from: {url} to: {dst}")
        with open(str(dst), "wb") as f:
            r = self.get_url(url, stream=True)
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
