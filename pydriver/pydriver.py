import platform
import os
import logging
import sys
from requests_html import HTMLSession
import fire
import shutil
from typing import List, Union
from packaging.version import parse
from zipfile import ZipFile
from pathlib import Path
import humanfriendly
from configobj import ConfigObj
import hashlib


class PyDriver:
    def __init__(self):
        self._drivers_home = Path(PyDriver._get_drivers_home())
        self._drivers_cfg = self._drivers_home / Path("drivers.ini")
        self._drivers_state = ConfigObj(str(self._drivers_cfg))
        self._cache_dir = Path.home() / Path(".pydriver_cache")
        self._session = HTMLSession()
        self._system_name = platform.uname().system.lower()
        self._system_arch = platform.uname().machine.replace("x86_", "")
        self._driver_os = {"Windows": [], "Darwin": [], "Linux": []}
        self._global_config = {
            "chrome": {
                "url": "http://chromedriver.storage.googleapis.com/index.html",
                "ignore_files": [
                    "index.html",
                    "notes",
                    "Parent Directory",
                    "icons",
                    "LATEST_RELEASE",
                ],
                "supported_archs": ["32", "64"],
                "supported_os": ["mac", "win", "linux"],
                "filename": Path("chromedriver")
            },
            "ie": "",
            "gecko": "https://github.com/mozilla/geckodriver/releases/",
            "phantomjs": "",
        }
        self._setup_dirs([self._drivers_home, self._cache_dir])

    @property
    def system_name(self):
        return self._system_name

    @system_name.setter
    def system_name(self, system_name: str):
        if system_name == "darwin":
            self._system_name = "mac"
        elif system_name == "windows":
            self._system_name = "win"
        else:
            self._system_name = "linux"

    def _setup_dirs(self, dirs: List[Path]):
        for dir_ in dirs:
            dir_.mkdir(parents=True, exist_ok=True)

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

    def _dl_driver(self, url: str, dst: Path) -> None:
        with open(str(dst), "wb") as f:
            r = self._get_url(url, stream=True)
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    def _filter_server_garbage(self, drivers: List) -> List:
        # drivers: List[Element] -> List[Element]
        return [
            [item.text, item.attrs["href"]]
            for item in drivers
            if not item.text.startswith(
                tuple(self._global_config["chrome"]["ignore_files"])
            )
        ]

    def _list_remote_chrome_drivers(self, print_output: bool = True) -> List[str]:
        r = self._get_url(self._global_config["chrome"]["url"])
        r.html.render(sleep=1)  # need time to render
        drivers = r.html.xpath("/html/body/table//tr/td[2]/a")
        drivers_versions = self._filter_server_garbage(drivers)
        if print_output:
            for driver_version in drivers_versions:
                print(driver_version[0])
        return drivers_versions

    def _get_newest_chrome_version(self) -> str:
        highest_v = parse("0.0.0.0")
        versions = self._list_remote_chrome_drivers(print_output=False)
        for version in versions:
            v = parse(version[0])
            if v > highest_v:
                highest_v = v
        return str(highest_v)

    def _get_chrome_driver(
        self, version: str, os_: str, arch: str
    ):
        # TODO: Verify wrong version given
        version = version or self._get_newest_chrome_version()
        os_ = os_ or self._system_name
        arch = arch or self._system_arch
        file_name = Path(f"chromedriver_{os_}{arch}.zip")
        url = f"{self._global_config['chrome']['url'].replace('index.html', '')}{version}/{file_name}"
        version_cache_dir = self._cache_dir / Path("chrome") / Path(version)
        zipfile_path = version_cache_dir / file_name
        self._setup_dirs([version_cache_dir])
        self._dl_driver(url, zipfile_path)
        self._update_driver(zipfile_path, "chrome", os_, arch, version)
        print(f"Downloaded chromedriver {version}::{os_}::{arch} from {url}")

    def _unzip_file(self, zipfile: Path) -> None:
        with ZipFile(str(zipfile), "r") as zip_ref:
            zip_ref.extractall(str(self._drivers_home))

    def _calculate_dir_size(self, startdir: Path) -> str:
        byte_size = sum(f.stat().st_size for f in startdir.glob("**/*") if f.is_file())
        return humanfriendly.format_size(byte_size)

    def _calculate_checksum(self, filepath: Path) -> str:
        with open(str(filepath), "rb") as f:
            bytes = f.read()
            return hashlib.md5(bytes).hexdigest()

    def _update_driver(self, zipfile_path: Path, driver_type: str, os_:str, arch:str, version: str):
        driver_location = self._drivers_home / self._global_config[driver_type]["filename"]
        if driver_location.is_file():
            os.remove(str(self._drivers_home / self._global_config[driver_type]["filename"]))
        self._unzip_file(zipfile_path)
        self._add_driver_to_ini(self._global_config[driver_type]["filename"], driver_type, os_, arch, version)

    def _read_drivers_from_ini(self):
        if not self._drivers_cfg.exists():
            self._exit("No drivers installed")
        for driver_type in self._drivers_state.sections:
            print(f"Type: {driver_type:<12}")
            for k, v in self._drivers_state[driver_type].items():
                print(f"{k:<13}: {v}")

    def _add_driver_to_ini(self, file_name: Path, driver_type: str, os_: str, arch:str, version:str) -> None:
        self._drivers_state[driver_type] = {
            "FILENAME": file_name,
            "VERSION": version,
            "OS": os_,
            "ARCHITECTURE": arch,
            "CHECKSUM": self._calculate_checksum(self._drivers_home / file_name),
        }
        self._drivers_state.write()

    def show_env(self) -> None:
        """Show where DRIVERS_HOME points"""
        print(
            f"WebDrivers are installed in: {self._drivers_home}, total size is: {self._calculate_dir_size(self._drivers_home)}"
        )
        print(
            f"PyDriver cache is in: {self._cache_dir}, total size is: {self._calculate_dir_size(self._cache_dir)}"
        )

    def installed_drivers(self) -> None:
        """List drivers installed at DRIVERS_HOME"""
        if not self._drivers_home.is_dir():
            PyDriver._exit(f"DRIVER_HOME directory does not exist")
        self._read_drivers_from_ini()

    def list_drivers(self, driver_type: str) -> None:
        """List drivers on remote server"""
        if driver_type == "chrome":
            self._list_remote_chrome_drivers()

    def install_driver(
        self,
        driver_type: str,
        version: Union[str, float, int] = "",
        os_: str = "",
        arch: str = "",
    ) -> None:
        """Download certain version of given WebDriver type"""
        if driver_type == "chrome":
            self._get_chrome_driver(str(version), os_, arch)




def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
