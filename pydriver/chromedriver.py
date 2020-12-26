import logging
import re
import xml.etree.ElementTree as ET

from pydriver.config import WebDriverType, pydriver_config
from pydriver.downloader import Downloader
from pydriver.support import Support
from pydriver.webdriver import WebDriver


class ChromeDriver:
    def __init__(self):
        self.logger = logging.getLogger("PyDriver")
        self.webdriver = WebDriver()
        self.downloader = Downloader()
        self.support = Support()

    def _parse_version_os_arch(self, webdriver_filename: str) -> None:
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/chromedriver_(linux|win|mac)(32|64)\.zip",
            webdriver_filename,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.webdriver.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, filename=f"chromedriver_{os_}{arch}.zip"
            )

    def get_driver(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.webdriver.validate_version_os_arch("chrome", version, os_, arch)
        url = f"{pydriver_config[WebDriverType.CHROME]['url']}/{version}/{file_name}"
        self.webdriver.get_driver("chrome", url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        # {8.1: {linux: [32, 64]}}
        r = self.downloader.get_url(pydriver_config[WebDriverType.CHROME]["url"])
        root = ET.fromstring(r.content)
        ns = root.tag.replace("ListBucketResult", "")
        for key in root.iter(f"{ns}Key"):
            self._parse_version_os_arch(key.text)
