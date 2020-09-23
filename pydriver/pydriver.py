import hashlib
import logging
import logging.handlers
import os
import platform
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from distutils.version import LooseVersion
from pathlib import Path
from typing import List, Tuple, Union
from zipfile import ZipFile

import fire
import humanfriendly
import requests
import tabulate
from configobj import ConfigObj


class PyDriver:
    _ENV_NAME = "DRIVERS_HOME"
    _WIN_EXTENSION = ".exe"
    _CONFIG_KEYS = [
        "DRIVER TYPE",
        "VERSION",
        "OS",
        "ARCHITECTURE",
        "FILENAME",
        "CHECKSUM",
    ]
    _LOG_FILENAME = "pydriver.log"

    def __init__(self):
        self._pd_logger = self._configure_logging()
        self._pd_logger.debug("{:=>10}Starting new request{:=>10}".format("", ""))
        self._drivers_home = Path(self._get_drivers_home())
        self._drivers_cfg = self._drivers_home / Path(".drivers.ini")
        self._drivers_state = ConfigObj(str(self._drivers_cfg))
        self._cache_dir = Path.home() / Path(".pydriver_cache")
        self._session = requests.Session()
        self.system_name = platform.uname().system
        self.system_arch = platform.uname().machine
        self._global_config = {
            "chrome": {
                "url": "https://chromedriver.storage.googleapis.com",
                "ignore_files": ["index.html", "notes", "Parent Directory", "icons", "LATEST_RELEASE"],
                "filename": Path("chromedriver"),
            },
            "ie": "",
            "gecko": "https://github.com/mozilla/geckodriver/releases/",
            "phantomjs": "",
        }
        self._versions_info = {}
        self._setup_dirs([self._drivers_home, self._cache_dir])
        self._pd_logger.debug(f"Identified OS: {self.system_name}")
        self._pd_logger.debug(f"Identified architecture: {self.system_arch}")

    @property
    def system_arch(self):
        return self._system_arch

    @system_arch.setter
    def system_arch(self, system_arch: str):
        if system_arch in ["x86_64", "AMD64"]:
            self._system_arch = "64"
        elif system_arch in ["i386", "i586", "32", "x86"]:
            self._system_arch = "32"
        else:
            self._exit(f"Unknown architecture: {system_arch}")
        self._pd_logger.debug(f"Current's OS architecture string: {system_arch} -> {self._system_arch} bit")

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
        elif system_name == "linux":
            self._system_name = "linux"
        else:
            self._exit(f"Unknown OS type: {system_name}")
        self._pd_logger.debug(f"Current's OS type string: {system_name} -> {self._system_name}")

    def _configure_logging(self):
        # Set up a specific logger with our desired output level
        pd_logger = logging.getLogger("DriverLogger")
        pd_logger.setLevel(logging.DEBUG)
        file_handler = logging.handlers.RotatingFileHandler(
            PyDriver._LOG_FILENAME, maxBytes=1024 * 1024 * 10, backupCount=5
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s - %(lineno)s - %(funcName)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        pd_logger.addHandler(file_handler)
        pd_logger.addHandler(console_handler)
        return pd_logger

    def _setup_dirs(self, dirs: List[Path]):
        for dir_ in dirs:
            dir_.mkdir(parents=True, exist_ok=True)

    def _exit(self, messages: Union[List, str] = "", exit_code: int = 1) -> None:
        if messages:
            if type(messages) == str:
                messages = [messages]
            for msg in messages:
                self._pd_logger.error(msg)
        sys.exit(exit_code)

    def _get_drivers_home(self) -> str:
        home = os.environ.get(PyDriver._ENV_NAME)
        self._pd_logger.debug(f"{PyDriver._ENV_NAME} set to {home}")
        if not home:
            self._exit("Env variable 'DRIVERS_HOME' not defined")
        return home

    def _get_url(self, url: str, stream=False):
        self._pd_logger.debug(f"Downloading: {url}")
        r = self._session.get(url, stream=stream)
        if r.status_code == 200:
            return r
        else:
            self._exit(f"Cannot download file {url}")

    def _dl_driver(self, url: str, dst: Path) -> None:
        self._pd_logger.debug(f"Downloading from: {url} to: {dst}")
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
        match = re.match(
            r"(([0-9]+\.){1,3}[0-9]+).*/chromedriver_(linux|win|mac)(32|64)\.zip",
            version_string,
        )
        if match:
            self.__def_update_version_dict(str(match.group(1)), str(match.group(3)), str(match.group(4)))

    def _get_remote_chrome_drivers_list(self) -> None:
        # {8.1: {linux: [32, 64]}}
        r = self._get_url(self._global_config["chrome"]["url"])
        root = ET.fromstring(r.content)
        ns = root.tag.replace("ListBucketResult", "")
        for key in root.iter(f"{ns}Key"):
            self.__parse_version_os_arch(key.text)

    def _get_newest_version(self) -> str:
        highest_v = str(sorted(self._versions_info.keys(), key=LooseVersion)[-1])
        self._pd_logger.debug(f"Highest version of driver is: {highest_v}")
        return highest_v

    def _validate_version_os_arch(self, version: str, os_: str, arch: str) -> Tuple[str, str, str]:
        errors = []
        version = version or self._get_newest_version()
        os_ = os_ or self.system_name
        arch = arch or self.system_arch
        self._pd_logger.debug(f"I will download following version: {version}, OS: {os_}, arch: {arch}")
        driver = self._drivers_state.get("chrome")
        if driver:
            if os_ == driver.get("OS") and arch == driver.get("ARCHITECTURE") and version == driver.get("VERSION"):
                self._pd_logger.info("Requested driver already installed")
                self._exit(exit_code=0)
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
        self._pd_logger.debug(f"Requested version: {version}, OS: {os_}, arch: {arch}")
        self._get_remote_chrome_drivers_list()
        version, os_, arch = self._validate_version_os_arch(version, os_, arch)
        file_name = Path(f"chromedriver_{os_}{arch}.zip")
        version_cache_dir = self._cache_dir / Path("chrome") / Path(version)
        zipfile_path = version_cache_dir / file_name
        if not (version_cache_dir / file_name).is_file():
            self._pd_logger.info("Requested driver not found in cache")
            url = f"{self._global_config['chrome']['url']}/{version}/{file_name}"
            self._setup_dirs([version_cache_dir])
            self._dl_driver(url, zipfile_path)
        else:
            self._pd_logger.debug("Chromedriver in cache")
        self._update_driver(zipfile_path, "chrome", os_, arch, version)
        self._pd_logger.info(f"Installed chromedriver:\nVERSION: {version}\nOS: {os_}\nARCHITECTURE: {arch}")

    def _unzip_file(self, zipfile: Path) -> None:
        with ZipFile(str(zipfile), "r") as zip_ref:
            zip_ref.extractall(str(self._drivers_home))
            self._pd_logger.debug(f"Unzipped {zipfile} to {self._drivers_home}")

    def _calculate_dir_size(self, startdir: Path) -> str:
        byte_size = sum(f.stat().st_size for f in startdir.glob("**/*") if f.is_file())
        return humanfriendly.format_size(byte_size)

    def _calculate_checksum(self, filepath: Path) -> str:
        with open(str(filepath), "rb") as f:
            bytes_ = f.read()
            checksum = hashlib.md5(bytes_).hexdigest()
            self._pd_logger.debug(f"Checksum of file {filepath}: {checksum}")
            return checksum

    def _update_driver(
        self,
        zipfile_path: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ):
        filename = self._global_config[driver_type]["filename"]
        if os_ == "win":
            filename = filename.with_suffix(PyDriver._WIN_EXTENSION)
        if driver_type in self._drivers_state.sections:
            old_driver_name = self._drivers_state[driver_type]["FILENAME"]
            self._delete_driver_files(old_driver_name)
        self._unzip_file(zipfile_path)
        self._add_driver_to_ini(filename, driver_type, os_, arch, version)

    def _print_drivers_from_ini(self):
        if not self._drivers_cfg.exists() or len(self._drivers_state.sections) == 0:
            self._exit("No drivers installed")
        values = []
        for driver_type in self._drivers_state.sections:
            values.append([driver_type] + [self._drivers_state[driver_type][v] for v in PyDriver._CONFIG_KEYS[1:]])
        self._pd_logger.info(tabulate.tabulate(values, headers=PyDriver._CONFIG_KEYS, showindex=True))

    def _add_driver_to_ini(
        self,
        file_name: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ) -> None:
        keys = PyDriver._CONFIG_KEYS[1:]
        self._drivers_state[driver_type] = dict(
            zip(
                keys,
                [
                    version,
                    os_,
                    arch,
                    file_name,
                    self._calculate_checksum(self._drivers_home / file_name),
                ],
            )
        )
        self._drivers_state.write()
        self._pd_logger.debug(f"Driver {driver_type} added to ini file")

    def _delete_driver_from_ini(self, driver_types: Tuple[Tuple[str]]) -> None:
        if not self._drivers_cfg.exists():
            self._exit("No drivers installed")
        if not driver_types:
            driver_types = self._drivers_state.sections.copy()
        for driver_type in driver_types:
            if driver_type not in self._drivers_state.sections:
                self._pd_logger.info(f"Driver: {driver_type}, is not installed")
            else:
                driver_filename = self._drivers_state[driver_type]["FILENAME"]
                self._drivers_state.pop(driver_type)
                self._pd_logger.debug(f"Driver {driver_type} removed from ini.")
                self._delete_driver_files(driver_filename)
                self._pd_logger.info(f"Driver: {driver_type}, deleted")
                self._drivers_state.write()

    def _delete_driver_files(self, filename: Path) -> None:
        filepath = self._drivers_home / filename
        if filepath.is_file():
            os.remove(str(filepath))
            self._pd_logger.debug(f"Driver file deleted: {filename}")
        else:
            self._pd_logger.debug(f"Driver file not found: {filename}")

    def _print_remote_drivers(self):
        values = []
        for version, v in self._versions_info.items():
            for os_, arch in v.items():
                values.append([version, os_, " ".join(arch)])
        values = sorted(values, key=lambda val: LooseVersion(val[0]))
        self._pd_logger.info(tabulate.tabulate(values, headers=PyDriver._CONFIG_KEYS[1:4], showindex=True))

    def show_env(self) -> None:
        """Show where DRIVERS_HOME points"""
        self._pd_logger.info(
            f"WebDrivers are installed in: {self._drivers_home}, total size is: "
            f"{self._calculate_dir_size(self._drivers_home)}"
        )
        self._pd_logger.info(
            f"PyDriver cache is in: {self._cache_dir}, total size is: {self._calculate_dir_size(self._cache_dir)}"
        )

    def installed_drivers(self) -> None:
        """List drivers installed at DRIVERS_HOME"""
        if not self._drivers_home.is_dir():
            self._exit("DRIVER_HOME directory does not exist")
        self._print_drivers_from_ini()

    def list_drivers(self, driver_type: str) -> None:
        """List drivers on remote server"""
        if driver_type == "chrome":
            self._get_remote_chrome_drivers_list()
            self._pd_logger.info("Available Chrome drivers:")
        self._print_remote_drivers()

    def install_driver(
        self,
        driver_type: str,
        version: Union[str, float, int] = "",
        os_: str = "",
        arch: str = "",
    ) -> None:
        """Download certain version of given WebDriver type"""
        if driver_type == "chrome":
            self._get_chrome_driver(str(version), str(os_), str(arch))

    def delete_driver(self, *driver_type: Tuple[str]) -> None:
        """Remove given driver-type or all installed drivers"""
        self._delete_driver_from_ini(driver_type)


def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
