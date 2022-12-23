import re
import xml.etree.ElementTree as ET

from pydriverr.config import WebDriverType
from pydriverr.custom_logger import logger
from pydriverr.downloader import Downloader
from pydriverr.webdriver import WebDriver


class EdgeDriver(WebDriver):
    """Handle Edge WebDriver"""

    def __init__(self):
        super().__init__()
        self.downloader = Downloader()

    def _parse_version_os_arch(self, file_name: str) -> None:
        """
        Parse edgedriver compressed file name

        :param file_name: Dict from GitHub API containing information about every release.
        :return: None
        """
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/edgedriver_(linux|win|mac|arm)(32|64|86)\.zip",
            file_name,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, file_name=f"edgedriver_{os_}{arch}.zip"
            )

    def get_remote_drivers_list(self) -> None:
        r = self.downloader.get_url(f"{WebDriverType.EDGE.url}/?comp=list")
        root = ET.fromstring(r.content)
        for key in root.iter("Name"):
            self._parse_version_os_arch(key.text)

    def install(self, version: str, os_: str, arch: str) -> None:
        logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.EDGE.drv_name, version, os_, arch)
        url = f"{WebDriverType.EDGE.url}/{version}/{file_name}"
        self.install_driver(WebDriverType.EDGE.drv_name, url, version, os_, arch, file_name)

    def update(self) -> None:
        self.generic_update(WebDriverType.EDGE.drv_name, self.get_remote_drivers_list, self.install)
