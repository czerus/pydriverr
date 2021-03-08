import logging
import re
import xml.etree.ElementTree as ET
from distutils.version import LooseVersion

from pydriver.config import WebDriverType, pydriver_config
from pydriver.downloader import Downloader
from pydriver.support import Support
from pydriver.webdriver import WebDriver


class EdgeDriver:
    def __init__(self):
        self.logger = logging.getLogger("PyDriver")
        self.webdriver = WebDriver()
        self.downloader = Downloader()
        self.support = Support()

    def _parse_version_os_arch(self, webdriver_filename: str) -> None:
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/edgedriver_(linux|win|mac|arm)(32|64|86)\.zip",
            webdriver_filename,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.webdriver.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, filename=f"edgedriver_{os_}{arch}.zip"
            )

    def get_driver(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.webdriver.validate_version_os_arch(
            WebDriverType.EDGE.drv_name, version, os_, arch
        )
        url = f"{pydriver_config[WebDriverType.EDGE]['url']}/{version}/{file_name}"
        self.webdriver.get_driver(WebDriverType.EDGE.drv_name, url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        r = self.downloader.get_url(f'{pydriver_config[WebDriverType.EDGE]["url"]}/?comp=list')
        root = ET.fromstring(r.content)
        for key in root.iter("Name"):
            self._parse_version_os_arch(key.text)

    def update(self) -> None:
        """Replace currently installed version of edgedriver with newest available"""
        self.logger.debug(f"Updating {WebDriverType.EDGE.drv_name}driver")
        driver_state = self.webdriver.drivers_state.get(WebDriverType.EDGE.drv_name)
        if not driver_state:
            self.logger.info(f"Driver {WebDriverType.EDGE.drv_name}driver is not installed")
            return
        local_version = driver_state.get("VERSION")
        if not local_version:
            self.logger.info("Corrupted .ini file")
            return
        self.get_remote_drivers_list()
        remote_version = self.webdriver.get_newest_version()
        if LooseVersion(local_version) >= LooseVersion(remote_version):
            self.logger.info(
                f"{WebDriverType.EDGE.drv_name}driver is already in newest version. Local: {local_version}, "
                f"remote: {remote_version}"
            )
        else:
            os_ = self.webdriver.drivers_state.get(WebDriverType.EDGE.drv_name, {}).get("OS")
            arch = self.webdriver.drivers_state.get(WebDriverType.EDGE.drv_name, {}).get("ARCHITECTURE")
            self.get_driver(remote_version, os_, arch)
            self.logger.info(f"Updated {WebDriverType.EDGE.drv_name}driver: {local_version} -> {remote_version}")
