import itertools
from enum import Enum
from typing import List


class WebDriverType(Enum):
    GECKO = ("gecko", ["geckodriver", "wires"])
    CHROME = ("chrome", ["chromedriver"])
    OPERA = ("opera", ["operadriver"])
    EDGE = ("edge", ["msedgedriver", "edgewebdriver"])

    def __init__(self, drv_name, drv_file_names):
        self.drv_name = drv_name
        self.drv_file_names = drv_file_names

    @staticmethod
    def list() -> List[str]:
        """Return list of supported WebDriver types"""
        return list(map(lambda c: c.drv_name, WebDriverType))

    @staticmethod
    def list_all_file_names() -> List[str]:
        """Return list of WebDriver file names"""
        return list(itertools.chain(*list(map(lambda c: c.drv_file_names, WebDriverType))))


pydriver_config = {
    WebDriverType.CHROME: {
        "url": "https://chromedriver.storage.googleapis.com",
        "ignore_files": ["index.html", "notes", "Parent Directory", "icons", "LATEST_RELEASE"],
    },
    WebDriverType.GECKO: {
        "url": "https://github.com/{owner}/{repo}",
    },
    WebDriverType.OPERA: {
        "url": "https://github.com/{owner}/{repo}",
    },
    WebDriverType.EDGE: {
        "url": "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver",
        "ignore_files": ["index.html", "LATEST_STABLE", "LATEST_UNKNOWN", "LICENSE", "LATEST_RELEASE", "credits.html"],
    },
}
