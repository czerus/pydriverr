import re
import xml.etree.ElementTree as ET

from pydriver.config import WebDriverType, pydriver_config
from pydriver.downloader import Downloader
from pydriver.webdriver import WebDriver


class EdgeDriver(WebDriver):
    def __init__(self):
        super().__init__()
        self.downloader = Downloader()

    def _parse_version_os_arch(self, webdriver_filename: str) -> None:
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/edgedriver_(linux|win|mac|arm)(32|64|86)\.zip",
            webdriver_filename,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, filename=f"edgedriver_{os_}{arch}.zip"
            )

    def install_driver(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.EDGE.drv_name, version, os_, arch)
        url = f"{pydriver_config[WebDriverType.EDGE]['url']}/{version}/{file_name}"
        self._install_driver(WebDriverType.EDGE.drv_name, url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        r = self.downloader.get_url(f'{pydriver_config[WebDriverType.EDGE]["url"]}/?comp=list')
        root = ET.fromstring(r.content)
        for key in root.iter("Name"):
            self._parse_version_os_arch(key.text)

    def update(self) -> None:
        """Replace currently installed version of edgedriver with newest available"""
        self.generic_update(WebDriverType.EDGE.drv_name, self.get_remote_drivers_list, self.install_driver)
