import itertools
import os
import sys
import tempfile
from enum import Enum
from typing import List


class WebDriverType(Enum):

    GECKO = (
        "gecko",
        ["geckodriver", "wires"],
        "https://github.com/{owner}/{repo}",
        "firefox --version",
    )
    CHROME = (
        "chrome",
        ["chromedriver"],
        "https://chromedriver.storage.googleapis.com",
        "google-chrome --version",
    )
    OPERA = (
        "opera",
        ["operadriver"],
        "https://github.com/{owner}/{repo}",
        "opera --version",
    )
    EDGE = (
        "edge",
        ["msedgedriver", "edgewebdriver"],
        "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver",
        "reg query HKCU\\Software\\Microsoft\\Edge\\BLBeacon /v version",
    )

    def __init__(self, drv_name: str, drv_file_names: List[str], url: str, cmd: str):
        self.drv_name = drv_name
        self.drv_file_names = drv_file_names
        self.url = url
        self.cmd = cmd

    @staticmethod
    def cmd_for_drv_name(driver_type: str) -> str:
        """
        Return command that runs web browser for given driver name.

        :param driver_type: Type of the WebDriver e.g. chrome, gecko
        :return: Command as string
        """
        for drv in WebDriverType:
            if drv.value[0] == driver_type:
                return drv.value[-1]  # last is command

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


LOGGING_CONF = {
    "handlers": [
        {"sink": sys.stdout, "format": "{message}", "level": 20},
        {
            "sink": os.path.join(tempfile.gettempdir(), "pydriverr.log"),
            "serialize": False,
            "rotation": "5MB",
            "compression": "zip",
        },
    ],
}
