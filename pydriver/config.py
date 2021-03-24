import itertools
from enum import Enum
from typing import List


class WebDriverType(Enum):

    GECKO = ("gecko", ["geckodriver", "wires"], "https://github.com/{owner}/{repo}")
    CHROME = (
        "chrome",
        ["chromedriver"],
        "https://chromedriver.storage.googleapis.com",
    )
    OPERA = ("opera", ["operadriver"], "https://github.com/{owner}/{repo}")
    EDGE = (
        "edge",
        ["msedgedriver", "edgewebdriver"],
        "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver",
    )

    def __init__(self, drv_name: str, drv_file_names: List[str], url: str):
        self.drv_name = drv_name
        self.drv_file_names = drv_file_names
        self.url = url

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
