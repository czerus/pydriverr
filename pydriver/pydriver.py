import hashlib
import logging
import os
import platform
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union, Tuple
from zipfile import ZipFile

import fire
import humanfriendly
import requests
from configobj import ConfigObj
from packaging.version import parse


class PyDriver:
    WIN_EXTENSION = ".exe"

    def __init__(self):
        self._drivers_home = Path(PyDriver._get_drivers_home())
        self._drivers_cfg = self._drivers_home / Path(".drivers.ini")
        self._drivers_state = ConfigObj(str(self._drivers_cfg))
        self._cache_dir = Path.home() / Path(".pydriver_cache")
        self._session = requests.Session()
        self.system_name = platform.uname().system
        self.system_arch = platform.uname().machine
        self._global_config = {
            "chrome": {
                "url": "https://chromedriver.storage.googleapis.com",
                "ignore_files": ["index.html", "notes", "Parent Directory", "icons", "LATEST_RELEASE",],
                "filename": Path("chromedriver"),
            },
            "ie": "",
            "gecko": "https://github.com/mozilla/geckodriver/releases/",
            "phantomjs": "",
        }
        self._versions_info = {}
        self._setup_dirs([self._drivers_home, self._cache_dir])

    @property
    def system_arch(self):
        return self._system_arch

    @system_arch.setter
    def system_arch(self, system_arch: str):
        self._system_arch = system_arch.replace("x86_", "").replace("AMD", "")

    @property
    def system_name(self):
        return self._system_name

    @system_name.setter
    def system_name(self, system_name: str):
        system_name = system_name.lower()
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
    def _exit(messages: Union[List, str]) -> None:
        if type(messages) == str:
            messages = [messages]
        for msg in messages:
            logging.error(msg)
        sys.exit(1)

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

    def __def_update_version_dict(self, version: str, os_: str, arch: str) -> None:
        if version not in self._versions_info:
            self._versions_info[version] = {os_: [arch]}
        else:
            if os_ not in self._versions_info[version]:
                self._versions_info[version][os_] = [arch]
            else:
                self._versions_info[version][os_].append(arch)

    def __parse_version_os_arch(self, version_string: str) -> None:
        match = re.match(r"(([0-9]+\.){1,3}[0-9]+).*/chromedriver_(linux|win|mac)(32|64)\.zip", version_string,)
        if match:
            self.__def_update_version_dict(str(match.group(1)), str(match.group(3)), str(match.group(4)))

    def _get_remote_chrome_drivers_list(self) -> None:
        # {8.1: {linux: [32, 64]}}
        r = self._get_url(self._global_config["chrome"]["url"])
        root = ET.fromstring(r.content)
        ns = root.tag.replace("ListBucketResult", "")
        for key in root.iter(f"{ns}Key"):
            self.__parse_version_os_arch(key.text)

    def _get_newest_chrome_version(self) -> str:
        highest_v = parse("0.0.0.0")
        for version in self._versions_info.keys():
            v = parse(version)
            if v > highest_v:
                highest_v = v
        return str(highest_v)

    def _validate_version_os_arch(self, version: str, os_: str, arch: str) -> Tuple[str, str, str]:
        errors = []
        version = version or self._get_newest_chrome_version()
        os_ = os_ or self.system_name
        arch = arch or self.system_arch
        if version not in self._versions_info:
            errors.append(f"There is no such version: {version}")
        else:
            if os_ not in self._versions_info[version]:
                errors.append(f"There is no such OS {os_} for version: {version}")
            else:
                if arch not in self._versions_info[version][os_]:
                    errors.append(f"There is no such arch {arch} for version {version} and OS: {os_}")
        if errors:
            self._exit(errors)
        return version, os_, arch

    def _get_chrome_driver(self, version: str, os_: str, arch: str) -> None:
        self._get_remote_chrome_drivers_list()
        version, os_, arch = self._validate_version_os_arch(version, os_, arch)
        file_name = Path(f"chromedriver_{os_}{arch}.zip")
        url = f"{self._global_config['chrome']['url']}/{version}/{file_name}"
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
            bytes_ = f.read()
            return hashlib.md5(bytes_).hexdigest()

    def _update_driver(self, zipfile_path: Path, driver_type: str, os_: str, arch: str, version: str):
        filename = self._global_config[driver_type]["filename"]
        if os_ == "win":
            filename = filename.with_suffix(PyDriver.WIN_EXTENSION)
        if driver_type in self._drivers_state.sections:
            old_driver_name = self._drivers_state[driver_type]["FILENAME"]
            self._delete_driver_files(old_driver_name)
        self._unzip_file(zipfile_path)
        self._add_driver_to_ini(filename, driver_type, os_, arch, version)

    def _read_drivers_from_ini(self):
        if not self._drivers_cfg.exists() or len(self._drivers_state.sections) == 0:
            self._exit("No drivers installed")
        for driver_type in self._drivers_state.sections:
            print(f"Type: {driver_type:<12}")
            for k, v in self._drivers_state[driver_type].items():
                print(f"{k:<13}: {v}")

    def _add_driver_to_ini(self, file_name: Path, driver_type: str, os_: str, arch: str, version: str) -> None:
        self._drivers_state[driver_type] = {
            "FILENAME": file_name,
            "VERSION": version,
            "OS": os_,
            "ARCHITECTURE": arch,
            "CHECKSUM": self._calculate_checksum(self._drivers_home / file_name),
        }
        self._drivers_state.write()

    def _delete_driver_from_ini(self, driver_types: List[str]) -> None:
        if not self._drivers_cfg.exists():
            self._exit("No drivers installed")
        for driver_type in driver_types:
            if driver_type not in self._drivers_state.sections:
                print(f"Driver: {driver_type}, is not installed")
            else:
                driver_filename = self._drivers_state[driver_type]["FILENAME"]
                self._drivers_state.pop(driver_type)
                self._delete_driver_files(driver_filename)
                print(f"Driver: {driver_type}, deleted")
            self._drivers_state.write()

    def _delete_driver_files(self, filename: Path) -> None:
        os.remove(str(self._drivers_home / filename))

    def _print_drivers(self):
        for version, v in self._versions_info.items():
            print(f"{version}:")
            for os_, arch in v.items():
                print(f"\t{os_}: {' '.join(arch)}")

    def show_env(self) -> None:
        """Show where DRIVERS_HOME points"""
        print(
            f"WebDrivers are installed in: {self._drivers_home}, total size is: {self._calculate_dir_size(self._drivers_home)}"
        )
        print(f"PyDriver cache is in: {self._cache_dir}, total size is: {self._calculate_dir_size(self._cache_dir)}")

    def installed_drivers(self) -> None:
        """List drivers installed at DRIVERS_HOME"""
        if not self._drivers_home.is_dir():
            PyDriver._exit(f"DRIVER_HOME directory does not exist")
        self._read_drivers_from_ini()

    def list_drivers(self, driver_type: str) -> None:
        """List drivers on remote server"""
        if driver_type == "chrome":
            self._get_remote_chrome_drivers_list()
            self._print_drivers()

    def install_driver(
        self, driver_type: str, version: Union[str, float, int] = "", os_: str = "", arch: str = "",
    ) -> None:
        """Download certain version of given WebDriver type"""
        if driver_type == "chrome":
            self._get_chrome_driver(str(version), str(os_), str(arch))

    def delete_driver(self, driver_type: str = "") -> None:
        """Remove given driver-type or all installed drivers"""
        if not driver_type:
            drivers_to_remove = self._global_config.keys()
        else:
            drivers_to_remove = [driver_type]
        self._delete_driver_from_ini(drivers_to_remove)


def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
