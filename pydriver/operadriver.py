import re
from distutils.version import LooseVersion
from typing import Dict

from pydriver.config import WebDriverType, pydriver_config
from pydriver.githubapi import GithubApi
from pydriver.webdriver import WebDriver


class OperaDriver(WebDriver):
    __OWNER = "operasoftware"
    __REPO = "operachromiumdriver"

    def __init__(self):
        super().__init__()
        self.githubapi = GithubApi(self.__OWNER, self.__REPO)

    def _parse_version_os_arch(self, releases_info: Dict) -> None:
        """Parse operadriver compressed file name"""
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
                        filename=filename,
                    )

    def install_driver(self, version: str, os_: str, arch: str) -> None:
        """Compose url and download compressed file"""
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.OPERA.drv_name, version, os_, arch)
        url = pydriver_config[WebDriverType.OPERA]["url"].format(owner=self.__OWNER, repo=self.__REPO)
        if version[0] == "0":  # old version "0.x.x" instead v. have just v
            prefix = "v"
        else:
            prefix = "v."
        url = url + f"/releases/download/{prefix}{version}/{file_name}"
        self._install_driver(WebDriverType.OPERA.drv_name, url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        """Get remote repository drivers list"""
        releases = self.githubapi.get_releases()
        self._parse_version_os_arch(releases)

    def update(self) -> None:
        """Replace currently installed version of operadriver with newest available"""
        self.logger.debug(f"Updating {WebDriverType.OPERA.drv_name}driver")
        driver_state = self.drivers_state.get(WebDriverType.OPERA.drv_name)
        if not driver_state:
            self.logger.info(f"Driver {WebDriverType.OPERA.drv_name}driver is not installed")
            return
        local_version = driver_state.get("VERSION")
        if not local_version:
            self.logger.info("Corrupted .ini file")
            return
        self.get_remote_drivers_list()
        remote_version = self.get_newest_version()
        if LooseVersion(local_version) >= LooseVersion(remote_version):
            self.logger.info(
                f"{WebDriverType.OPERA.drv_name}driver is already in newest version. "
                f"Local: {local_version}, remote: {remote_version}"
            )
        else:
            os_ = self.drivers_state.get(WebDriverType.OPERA.drv_name, {}).get("OS")
            arch = self.drivers_state.get(WebDriverType.OPERA.drv_name, {}).get("ARCHITECTURE")
            self.install_driver(remote_version, os_, arch)
            self.logger.info(f"Updated {WebDriverType.OPERA.drv_name}driver: {local_version} -> {remote_version}")
