from loguru import logger

from pydriver.downloader import Downloader
from pydriver.pydriver_types import ReleasesInfo


class GithubApi:
    """
    Helper class to download from GitHub.

    Uses internally `Downloader` class
    """

    API_URL = "https://api.github.com/repos/{owner}/{repo}"

    def __init__(self, owner: str, repo: str):
        """
        Init class

        :param owner: Owner of the GitHub repository
        :param repo: Name of the GitHub repository
        """
        self._downloader = Downloader()
        self._api_url = self.API_URL.format(owner=owner, repo=repo)

    def get_releases(self) -> ReleasesInfo:
        """
        Download list of releases

        :return: Dictionary with of given repo releases
        """
        # Skip asc files that are used to verify the archive
        releases = {}
        url_postfix = "/releases"
        r = self._downloader.get_url(self._api_url + url_postfix).json()
        for release in r:
            releases[release.get("tag_name")] = [
                asset.get("name") for asset in release.get("assets") if not asset.get("name").endswith(".asc")
            ]
        logger.debug(releases)
        return releases
