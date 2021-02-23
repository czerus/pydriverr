import logging
import re
from distutils.version import LooseVersion
from typing import Dict

from pydriver.config import WebDriverType, pydriver_config
from pydriver.githubapi import GithubApi
from pydriver.support import Support
from pydriver.webdriver import WebDriver


class GeckoDriver:

    __OWNER = "mozilla"
    __REPO = "geckodriver"

    def __init__(self):
        self.logger = logging.getLogger("PyDriver")
        self.webdriver = WebDriver()
        self.support = Support()
        self.githubapi = GithubApi(self.__OWNER, self.__REPO)

    def _parse_version_os_arch(self, releases_info: Dict) -> None:
        for version_tag, filenames in releases_info.items():
            for filename in filenames:
                match = re.match(
                    # DOESNT MATCH: "geckodriver-0.8.0-OSX.gz"
                    r"(geckodriver|wires)-.*?-(linux|win|macos|macOS|OSX|osx|arm)(32|64|7hf)*\.(.*)",
                    filename,
                )
                if match:
                    os_ = str(match.group(2))
                    self.webdriver.update_version_dict(
                        version=version_tag.replace("v", ""),
                        os_="mac" if os_.lower() in ["osx", "mac", "macos"] else os_,
                        arch=str(match.group(3) or ""),
                        filename=filename,
                    )

    def get_driver(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.webdriver.validate_version_os_arch(
            WebDriverType.GECKO.drv_name, version, os_, arch
        )
        url = pydriver_config[WebDriverType.GECKO]["url"].format(owner=self.__OWNER, repo=self.__REPO)
        url = url + f"/releases/download/v{version}/{file_name}"
        self.webdriver.get_driver("gecko", url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        releases = self.githubapi.get_releases()
        self._parse_version_os_arch(releases)

    def update(self) -> None:
        """Replace currently installed version of geckodriver with newest available"""
        self.logger.debug("Updating geckodriver")
        driver_state = self.webdriver.drivers_state.get(WebDriverType.GECKO.drv_name)
        if not driver_state:
            self.logger.info("Driver geckodriver is not installed")
            return
        local_version = driver_state.get("VERSION")
        if not local_version:
            self.logger.info("Corrupted .ini file")
            return
        self.get_remote_drivers_list()
        remote_version = self.webdriver.get_newest_version()
        if not local_version:
            self.support.exit("Corrupted .ini file")
        if LooseVersion(local_version) >= LooseVersion(remote_version):
            self.logger.info(
                f"geckodriver is already in newest version. Local: {local_version}, remote: {remote_version}"
            )
        else:
            os_ = self.webdriver.drivers_state.get(WebDriverType.GECKO.drv_name, {}).get("OS")
            arch = self.webdriver.drivers_state.get(WebDriverType.GECKO.drv_name, {}).get("ARCHITECTURE")
            self.get_driver(remote_version, os_, arch)
            self.logger.info(f"Updated geckodriver: {local_version} -> {remote_version}")
