import gzip
import logging
import os
import platform
import shutil
import tempfile
from distutils.version import LooseVersion
from pathlib import Path
from typing import Tuple

import tabulate
from configobj import ConfigObj

from pydriver.downloader import Downloader
from pydriver.support import Support


class WebDriver:
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

    def __init__(self):
        self._logger = logging.getLogger("PyDriver")
        self._support = Support()
        self._downloader = Downloader()
        self.drivers_home = Path(self._get_drivers_home())
        self._drivers_cfg = self.drivers_home / Path(".drivers.ini")
        self.drivers_state = ConfigObj(str(self._drivers_cfg))
        self.cache_dir = Path.home() / Path(".pydriver_cache")
        self.system_name = platform.uname().system
        self.system_arch = platform.uname().machine
        self._versions_info = {}
        self._support.setup_dirs([self.drivers_home, self.cache_dir])
        self._logger.debug(f"Identified OS: {self.system_name}")
        self._logger.debug(f"Identified architecture: {self.system_arch}")

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
            self._support.exit(f"Unknown architecture: {system_arch}")
        self._logger.debug(f"Current's OS architecture string: {system_arch} -> {self._system_arch} bit")

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
            self._support.exit(f"Unknown OS type: {system_name}")
        self._logger.debug(f"Current's OS type string: {system_name} -> {self._system_name}")

    def _get_drivers_home(self) -> str:
        home = os.environ.get(WebDriver._ENV_NAME)
        self._logger.debug(f"{WebDriver._ENV_NAME} set to {home}")
        if not home:
            self._support.exit("Env variable 'DRIVERS_HOME' not defined")
        return home

    def update_version_dict(self, version: str, os_: str, arch: str, filename: str) -> None:
        # {version: {os: {arch: filename, arch2: filename}}}
        if version not in self._versions_info:
            self._versions_info[version] = {os_: {arch: filename}}
        else:
            if os_ not in self._versions_info[version]:
                self._versions_info[version][os_] = {arch: filename}
            else:
                self._versions_info[version][os_][arch] = filename

    def get_newest_version(self) -> str:
        highest_v = str(sorted(self._versions_info.keys(), key=LooseVersion)[-1])
        self._logger.debug(f"Highest version of driver is: {highest_v}")
        return highest_v

    def validate_version_os_arch(
        self, driver_type: str, version: str, os_: str, arch: str
    ) -> Tuple[str, str, str, Path]:
        errors = []
        version = version or self.get_newest_version()
        os_ = os_ or self.system_name
        arch = arch or self.system_arch
        if driver_type == "gecko" and os_ == "mac":
            arch = ""  # gecko does not have arch for mac
        self._logger.debug(f"I will download following version: {version}, OS: {os_}, arch: {arch}")
        driver = self.drivers_state.get(driver_type)
        if driver:
            if os_ == driver.get("OS") and arch == driver.get("ARCHITECTURE") and version == driver.get("VERSION"):
                self._logger.info("Requested driver already installed")
                self._support.exit(exit_code=0)
        if version not in self._versions_info:
            errors.append(f"There is no such version: {version}")
        else:
            if os_ not in self._versions_info[version]:
                errors.append(f"There is no such OS {os_} for version: {version}")
            else:
                if arch not in self._versions_info[version][os_]:
                    errors.append(f"There is no such arch {arch} for version {version} and OS: {os_}")
        if errors:
            self._support.exit(errors)
        return version, os_, arch, Path(self._versions_info[version][os_][arch])

    def get_driver(self, driver_type: str, url: str, version: str, os_: str, arch: str, file_name: Path) -> None:
        version_cache_dir = self.cache_dir / Path(driver_type) / Path(version)
        zipfile_path = version_cache_dir / file_name
        if not (version_cache_dir / file_name).is_file():
            self._logger.info("Requested driver not found in cache")
            self._support.setup_dirs([version_cache_dir])
            self._downloader.dl_driver(url, zipfile_path)
        else:
            self._logger.debug(f"{driver_type}driver in cache")
        self.update_driver(zipfile_path, driver_type, os_, arch, version)
        self._logger.info(f"Installed {driver_type}driver:\nVERSION: {version}\nOS: {os_}\nARCHITECTURE: {arch}")

    @staticmethod
    def __unpack_gz(arc_path, dst_dir):
        with gzip.open(arc_path, "rb") as gz:
            content = gz.read()
        with open(Path(dst_dir) / Path(arc_path).name.replace(".gz", ""), "wb") as f:
            f.write(content)

    def _unpack(self, archive_path: Path, working_dir: str):
        compression_frmts = [frmt[0] for frmt in shutil.get_unpack_formats()]
        if "gz" not in compression_frmts:
            shutil.register_unpack_format("gz", ["gz"], WebDriver.__unpack_gz)
        shutil.unpack_archive(archive_path, extract_dir=working_dir)
        self._logger.debug(f"Uncompressed {archive_path} to {self.drivers_home}")

    def update_driver(
        self,
        archive_path: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ):
        if driver_type in self.drivers_state.sections:
            old_driver_name = self.drivers_state[driver_type]["FILENAME"]
            self._delete_driver_files(old_driver_name)
        with tempfile.TemporaryDirectory() as tmpdir:
            self._unpack(archive_path, tmpdir)
            uncompressed_file = Path(os.listdir(tmpdir)[0])
            src = tmpdir / uncompressed_file
            if not src.is_file():  # if file is inside nested folder
                uncompressed_file = Path(os.listdir(src)[0])
                src = src / uncompressed_file
            dst = self.drivers_home / uncompressed_file
            shutil.copyfile(src, dst)

        self._add_driver_to_ini(uncompressed_file, driver_type, os_, arch, version)

    def print_drivers_from_ini(self):
        if not self._drivers_cfg.exists() or len(self.drivers_state.sections) == 0:
            self._support.exit("No drivers installed")
        values = []
        for driver_type in self.drivers_state.sections:
            values.append([driver_type] + [self.drivers_state[driver_type][v] for v in WebDriver._CONFIG_KEYS[1:]])
        self._logger.info(tabulate.tabulate(values, headers=WebDriver._CONFIG_KEYS, showindex=True))

    def _add_driver_to_ini(
        self,
        file_name: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ) -> None:
        keys = WebDriver._CONFIG_KEYS[1:]
        self.drivers_state[driver_type] = dict(
            zip(
                keys,
                [
                    version,
                    os_,
                    arch,
                    file_name,
                    self._support.calculate_checksum(self.drivers_home / file_name),
                ],
            )
        )
        self.drivers_state.write()
        self._logger.debug(f"Driver {driver_type} added to ini file")

    def _delete_driver_files(self, filename: Path) -> None:
        filepath = self.drivers_home / filename
        if filepath.is_file():
            os.remove(str(filepath))
            self._logger.debug(f"Driver file deleted: {filename}")
        else:
            self._logger.debug(f"Driver file not found: {filename}")

    def clear_cache(self):
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def delete_drivers(self, driver_types_to_delete: Tuple[str]) -> None:
        if not self._drivers_cfg.exists():
            self._support.exit("No drivers installed")
        if len(driver_types_to_delete) == 0:
            driver_types_to_delete = self.drivers_state.sections.copy()
        for driver_type in driver_types_to_delete:
            if driver_type not in self.drivers_state.sections:
                self._logger.info(f"Driver: {driver_type} is not installed")
            else:
                driver_filename = self.drivers_state[driver_type]["FILENAME"]
                self.drivers_state.pop(driver_type)
                self._logger.debug(f"Driver {driver_type} removed from ini")
                self._delete_driver_files(driver_filename)
                self._logger.info(f"Driver: {driver_type} deleted")
                self.drivers_state.write()

    def print_remote_drivers(self):
        values = []
        for version, version_data in self._versions_info.items():
            for os_, os_data in version_data.items():
                values.append([version, os_, " ".join(os_data.keys())])
        values = sorted(values, key=lambda val: LooseVersion(val[0]))
        self._logger.info(tabulate.tabulate(values, headers=WebDriver._CONFIG_KEYS[1:4], showindex=True))
