import itertools
from enum import Enum
from typing import List, Union


class WebDriverType(Enum):

    GECKO = ("gecko", ["geckodriver", "wires"], "https://github.com/{owner}/{repo}")
    CHROME = (
        "chrome",
        ["chromedriver"],
        "https://chromedriver.storage.googleapis.com",
        ["index.html", "notes", "Parent Directory", "icons", "LATEST_RELEASE"],
    )
    OPERA = ("opera", ["operadriver"], "https://github.com/{owner}/{repo}")
    EDGE = (
        "edge",
        ["msedgedriver", "edgewebdriver"],
        "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver",
        ["index.html", "LATEST_STABLE", "LATEST_UNKNOWN", "LICENSE", "LATEST_RELEASE", "credits.html"],
    )

    def __init__(self, drv_name: str, drv_file_names: List[str], url: str, ignore_files: Union[None, List[str]] = None):
        self.drv_name = drv_name
        self.drv_file_names = drv_file_names
        self.url = url
        self.ignore_files = ignore_files

    @staticmethod
    def list() -> List[str]:
        """
        Return list of supported WebDriver types

        :return: List of all drv_names in enum
        """
        return list(map(lambda c: c.drv_name, WebDriverType))

    @staticmethod
    def list_all_file_names() -> List[str]:
        """
        Return list of WebDriver file names

        :return: List of all drv_file_names in enum
        """
        return list(itertools.chain(*list(map(lambda c: c.drv_file_names, WebDriverType))))
