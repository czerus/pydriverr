import logging
from typing import Dict, List

from pydriver.downloader import Downloader


class GithubApi:

    API_URL = "https://api.github.com/repos/{owner}/{repo}"

    def __init__(self, owner: str, repo: str):
        self._logger = logging.getLogger("PyDriver")
        self._downloader = Downloader()
        self._api_url = self.API_URL.format(owner=owner, repo=repo)

    def get_releases(self) -> Dict[str, List[str]]:
        # Skip asc files that are used to verify the archive
        releases = {}
        url_postfix = "/releases"
        r = self._downloader.get_url(self._api_url + url_postfix).json()
        for release in r:
            releases[release.get("tag_name")] = [
                asset.get("name") for asset in release.get("assets") if not asset.get("name").endswith(".asc")
            ]
        self._logger.debug(releases)
        return releases
