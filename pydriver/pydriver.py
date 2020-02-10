import platform
import os
import logging
import sys
from requests_html import HTMLSession
import fire
import shutil
from typing import List


class PyDriver:
    def __init__(self):
        self._session = HTMLSession()
        self._system_name = platform.system()
        self._drivers_home = PyDriver._get_drivers_home()
        self._driver_os = {"Windows": [], "Darwin": [], "Linux": []}
        self._drivers_url = {
            "chrome": {
                "url": "http://chromedriver.storage.googleapis.com/index.html",
                # "version_url": "http://chromedriver.storage.googleapis.com/index.html?path=/",
                "ignore_files": [
                    "index.html",
                    "notes",
                    "Parent Directory",
                    "icons",
                    "LATEST_RELEASE",
                ],
            },
            "ie": "",
            "gecko": "https://github.com/mozilla/geckodriver/releases/",
            "phantomjs": "",
        }

    @staticmethod
    def _exit(message: str) -> None:
        logging.error(message)
        sys.exit(0)

    @staticmethod
    def _get_drivers_home() -> str:
        home = os.environ.get("DRIVERS_HOME")
        if not home:
            PyDriver._exit("Env variable 'DRIVERS_HOME' not defined")
        return home

    def _get_url(self, url: str):
        r = self._session.get(url)
        if r.status_code == 200:
            return r
        else:
            PyDriver._exit(f"Cannot download file {url}")

    def _dl_driver(self, url: str, dst: str) -> None:
        with open(dst, "wb") as f:
            r = self._get_url(url)
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    def _filter_server_garbage(self, drivers: List) -> List:
        # drivers: List[Element] -> List[Element]
        return [
            [item.text, item.attrs["href"]]
            for item in drivers
            if not item.text.startswith(
                tuple(self._drivers_url["chrome"]["ignore_files"])
            )
        ]

    def _list_chrome_drivers(self):
        r = self._get_url(self._drivers_url["chrome"]["url"])
        r.html.render(sleep=0.5)  # need time to render
        drivers = r.html.xpath("/html/body/table//tr/td[2]/a")
        for driver_version in self._filter_server_garbage(drivers):
            print(driver_version[0])

    def show_home(self) -> None:
        """Show where DRIVERS_HOME points"""
        print(f"WebDrivers are installed in: {self._drivers_home}")

    def list_local_drivers(self) -> None:
        """List drivers installed at DRIVERS_HOME"""
        if not os.path.isdir(self._drivers_home):
            PyDriver._exit(f"DRIVER_HOME directory does not exist")
        drivers = os.listdir(self._drivers_home)
        print(f"Found {len(drivers)} drivers")
        print("\n".join(drivers))

    def list_drivers(self, driver_type: str) -> None:
        if driver_type == "chrome":
            self._list_chrome_drivers()

    def get_driver(self, driver_type: str, version: str) -> None:
        pass


def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
