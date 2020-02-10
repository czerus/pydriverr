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
        self._system_name = platform.uname().system.lower()
        self._system_arch = platform.uname().machine.replace("x86_", "")
        self._drivers_home = PyDriver._get_drivers_home()
        self._driver_os = {"Windows": [], "Darwin": [], "Linux": []}
        self._drivers_url = {
            "chrome": {
                "url": "http://chromedriver.storage.googleapis.com/index.html",
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

    def _get_url(self, url: str, stream=False):
        r = self._session.get(url, stream=stream)
        if r.status_code == 200:
            return r
        else:
            PyDriver._exit(f"Cannot download file {url}")

    def _dl_driver(self, url: str, dst: str) -> None:
        with open(dst, "wb") as f:
            r = self._get_url(url, stream=True)
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

    def _get_chrome_driver(self, version, os_, arch):
        os_ = os_ or self._system_name
        arch = arch or self._system_arch
        file_name = f"chromedriver_{os_}{arch}.zip"
        url = f"{self._drivers_url['chrome']['url'].replace('index.html', '')}{version}/{file_name}"
        self._dl_driver(url, os.path.join(self._drivers_home, file_name))
        print(f"Downloaded {file_name}")

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

    def get_driver(self, driver_type: str, version: str, os_=None, arch=None) -> None:
        """Download certain version of given WebDriver type"""
        if driver_type == "chrome":
            self._get_chrome_driver(version, os_, arch)


def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
