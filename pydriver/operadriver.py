import re
from typing import Dict

from pydriver.config import WebDriverType
from pydriver.githubapi import GithubApi
from pydriver.webdriver import WebDriver


class OperaDriver(WebDriver):
    """Handle Opera WebDriver"""

    __OWNER = "operasoftware"
    __REPO = "operachromiumdriver"

    def __init__(self):
        super().__init__()
        self.githubapi = GithubApi(self.__OWNER, self.__REPO)

    def _parse_version_os_arch(self, releases_info: Dict) -> None:
        """
        Parse operadriver compressed file name

        :param releases_info: Dict from GitHub API containing information about every release. Key is version tag.
        :return: None
        """
        for version_tag, filenames in releases_info.items():
            for filename in filenames:
                match = re.match(
                    r"(operadriver)_(linux|win|mac)(32|64)*\.(.*)",
                    filename,
                )
                if match:
                    version = re.search(r"[0-9]+(\.[0-9]+)+", version_tag)  # search only for version number
                    os_ = str(match.group(2))
                    self.update_version_dict(
                        version=version.group(0),
                        os_=os_,
                        arch=str(match.group(3)),
                        file_name=filename,
                    )

    def get_remote_drivers_list(self) -> None:
        releases = self.githubapi.get_releases()
        self._parse_version_os_arch(releases)

    def install(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.OPERA.drv_name, version, os_, arch)
        url = WebDriverType.OPERA.url.format(owner=self.__OWNER, repo=self.__REPO)
        if version[0] == "0":  # old version "0.x.x" instead v. have just v
            prefix = "v"
        else:
            prefix = "v."
        url = url + f"/releases/download/{prefix}{version}/{file_name}"
        self.install_driver(WebDriverType.OPERA.drv_name, url, version, os_, arch, file_name)

    def update(self) -> None:
        self.generic_update(WebDriverType.OPERA.drv_name, self.get_remote_drivers_list, self.install)
