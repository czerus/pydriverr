from enum import Enum
from typing import List


class WebDriverType(Enum):
    CHROME = "chrome"
    GECKO = "gecko"
    OPERA = "opera"

    @staticmethod
    def list() -> List[str]:
        """Return list of supported WebDriver types"""
        return list(map(lambda c: c.value, WebDriverType))


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
}
