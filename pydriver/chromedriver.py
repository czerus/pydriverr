import re
import xml.etree.ElementTree as ET
from distutils.version import LooseVersion

from pydriver.config import WebDriverType, pydriver_config
from pydriver.downloader import Downloader
from pydriver.webdriver import WebDriver


class ChromeDriver(WebDriver):
    def __init__(self):
        super().__init__()
        self.downloader = Downloader()

    def _parse_version_os_arch(self, webdriver_filename: str) -> None:
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/chromedriver_(linux|win|mac)(32|64)\.zip",
            webdriver_filename,
        )
        if match:
            os_ = str(match.group(3))
            arch = str(match.group(4))
            self.update_version_dict(
                version=str(match.group(1)), os_=os_, arch=arch, filename=f"chromedriver_{os_}{arch}.zip"
            )

    def install_driver(self, version: str, os_: str, arch: str) -> None:
        self.logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self.get_remote_drivers_list()
        version, os_, arch, file_name = self.validate_version_os_arch("chrome", version, os_, arch)
        url = f"{pydriver_config[WebDriverType.CHROME]['url']}/{version}/{file_name}"
        self._install_driver("chrome", url, version, os_, arch, file_name)

    def get_remote_drivers_list(self) -> None:
        # {8.1: {linux: [32, 64]}}
        r = self.downloader.get_url(pydriver_config[WebDriverType.CHROME]["url"])
        root = ET.fromstring(r.content)
        ns = root.tag.replace("ListBucketResult", "")
        for key in root.iter(f"{ns}Key"):
            self._parse_version_os_arch(key.text)

    def update(self) -> None:
        """Replace currently installed version of chromedriver with newest available"""
        self.logger.debug("Updating chromedriver")
        driver_state = self.drivers_state.get(WebDriverType.CHROME.drv_name)
        if not driver_state:
            self.logger.info("Driver chromedriver is not installed")
            return
        local_version = driver_state.get("VERSION")
        if not local_version:
            self.logger.info("Corrupted .ini file")
            return
        self.get_remote_drivers_list()
        remote_version = self.get_newest_version()
        if LooseVersion(local_version) >= LooseVersion(remote_version):
            self.logger.info(
                f"chromedriver is already in newest version. Local: {local_version}, remote: {remote_version}"
            )
        else:
            os_ = self.drivers_state.get(WebDriverType.CHROME.drv_name, {}).get("OS")
            arch = self.drivers_state.get(WebDriverType.CHROME.drv_name, {}).get("ARCHITECTURE")
            self.install_driver(remote_version, os_, arch)
            self.logger.info(f"Updated chromedriver: {local_version} -> {remote_version}")
