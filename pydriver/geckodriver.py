import re
from typing import Dict

from pydriver.config import WebDriverType, pydriver_config
from pydriver.githubapi import GithubApi
from pydriver.webdriver import WebDriver


class GeckoDriver(WebDriver):
    """Handle Gecko WebDriver"""

    __OWNER = "mozilla"
    __REPO = "geckodriver"

    def __init__(self):
        super().__init__()
        self.githubapi = GithubApi(self.__OWNER, self.__REPO)

    def _parse_version_os_arch(self, releases_info: Dict) -> None:
        """
        Parse geckodriver compressed file name

        :param releases_info: Dict from GitHub API containing information about every release. Key is version tag.
        :return: None
        """
        for version_tag, filenames in releases_info.items():
            for filename in filenames:
                match = re.match(
                    # DOESNT MATCH: "geckodriver-0.8.0-OSX.gz"
                    r"(geckodriver|wires)-.*?-(linux|win|macos|macOS|OSX|osx|arm)(32|64|7hf)*\.(.*)",
                    filename,
                )
                if match:
                    os_ = str(match.group(2))
                    self.update_version_dict(
                        version=version_tag.replace("v", ""),
                        os_="mac" if os_.lower() in ["osx", "mac", "macos"] else os_,
                        arch=str(match.group(3) or ""),
                        file_name=filename,
                    )

    def get_remote_drivers_list(self) -> None:
        releases = self.githubapi.get_releases()
        self._parse_version_os_arch(releases)

    def install(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.GECKO.drv_name, version, os_, arch)
        url = pydriver_config[WebDriverType.GECKO]["url"].format(owner=self.__OWNER, repo=self.__REPO)
        url = url + f"/releases/download/v{version}/{file_name}"
        self.install_driver("gecko", url, version, os_, arch, file_name)

    def update(self) -> None:
        self.generic_update(WebDriverType.GECKO.drv_name, self.get_remote_drivers_list, self.install)
