from enum import Enum


class WebDriverType(Enum):
    CHROME = "chrome"
    GECKO = "gecko"


pydriver_config = {
    WebDriverType.CHROME: {
        "url": "https://chromedriver.storage.googleapis.com",
        "ignore_files": ["index.html", "notes", "Parent Directory", "icons", "LATEST_RELEASE"],
    },
    WebDriverType.GECKO: {
        "url": "https://github.com/{owner}/{repo}",
    },
}
