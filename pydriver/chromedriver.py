import re
import xml.etree.ElementTree as ET

from loguru import logger

from pydriver.config import WebDriverType
from pydriver.downloader import Downloader
from pydriver.webdriver import WebDriver


class ChromeDriver(WebDriver):
    """Handle Chrome WebDriver"""

    def __init__(self):
        super().__init__()
        self.downloader = Downloader()

    def _parse_version_os_arch(self, file_name: str) -> None:
        """
        Parse chromedriver compressed file name

        :param file_name: Name of the compressed file.
        :return: None
        """
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/chromedriver_(linux|win|mac)(32|64)\.zip",
            file_name,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, file_name=f"chromedriver_{os_}{arch}.zip"
            )

    def get_remote_drivers_list(self) -> None:
        r = self.downloader.get_url(WebDriverType.CHROME.url)
        root = ET.fromstring(r.content)
        ns = root.tag.replace("ListBucketResult", "")
        for key in root.iter(f"{ns}Key"):
            self._parse_version_os_arch(key.text)

    def install(self, version: str, os_: str, arch: str) -> None:
        logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch(WebDriverType.CHROME.drv_name, version, os_, arch)
        url = f"{WebDriverType.CHROME.url}/{version}/{file_name}"
        self.install_driver(WebDriverType.CHROME.drv_name, url, version, os_, arch, file_name)

    def update(self) -> None:
        self.generic_update(WebDriverType.CHROME.drv_name, self.get_remote_drivers_list, self.install)
