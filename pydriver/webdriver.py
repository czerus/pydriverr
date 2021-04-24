import gzip
import logging
import os
import platform
import re
import shutil
import tempfile
from distutils.version import LooseVersion
from pathlib import Path
from typing import Tuple

import tabulate
from configobj import ConfigObj

from pydriver.config import WebDriverType
from pydriver.downloader import Downloader
from pydriver.pydriver_types import Drivers, FnInstall, FnRemoteDriversList
from pydriver.support import Support


class WebDriver:
    """Base class for all WebDrivers implementing many common methods"""

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
        self.logger = logging.getLogger("PyDriver")
        self.support = Support()
        self._downloader = Downloader()
        self.drivers_home = Path(self._get_drivers_home())
        self._drivers_cfg = self.drivers_home / Path(".drivers.ini")
        self.drivers_state = ConfigObj(str(self._drivers_cfg))
        self.cache_dir = Path.home() / Path(".pydriver_cache")
        self.system_name = platform.uname().system
        self.system_arch = platform.uname().machine
        self._versions_info = {}
        self.support.setup_dirs([self.drivers_home, self.cache_dir])
        self.logger.debug(f"Identified OS: {self.system_name}")
        self.logger.debug(f"Identified architecture: {self.system_arch}")

    @property
    def system_arch(self):
        return self._system_arch

    @system_arch.setter
    def system_arch(self, system_arch: str):
        # TODO: what about arm arch?
        # TODO: this check doesn't make sense at this point. There are 2 scenarios for installation:
        # * specify os and arch during install - then we do not care about current system architecture so way
        #   fail the whole operation? This shouldn`t be run at the init of WebDriver class then
        # * do not specify system or arch - then we want to install webdriver for current os and arch. Then we would
        #   also need to be able to discover ARM arch and system name.
        if system_arch in ["x86_64", "AMD64"]:
            self._system_arch = "64"
        elif system_arch in ["i386", "i586", "32", "x86"]:
            self._system_arch = "32"
        else:
            self.support.exit(f"Unknown architecture: {system_arch}")
        self.logger.debug(f"Current's OS architecture string: {system_arch} -> {self._system_arch} bit")

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
            self.support.exit(f"Unknown OS type: {system_name}")
        self.logger.debug(f"Current's OS type string: {system_name} -> {self._system_name}")

    def _get_drivers_home(self) -> str:
        """
        Get from environment variables dir where drivers will be installed.

        :return: Path to installation dir
        """
        home = os.environ.get(WebDriver._ENV_NAME)
        self.logger.debug(f"{WebDriver._ENV_NAME} set to {home}")
        if not home:
            self.support.exit("Env variable 'DRIVERS_HOME' not defined")
        return home

    def _add_driver_to_ini(
        self,
        file_name: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ) -> None:
        """
        Add info about newly installed driver to configuration .ini file

        :param file_name: Name of the WebDriver file
        :param driver_type: Type of the WebDriver e.g. chrome
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :param version: Version of the installed WebDriver
        :return: None
        """
        keys = WebDriver._CONFIG_KEYS[1:]
        self.drivers_state[driver_type] = dict(
            zip(
                keys,
                [
                    version,
                    os_,
                    arch,
                    file_name,
                    self.support.calculate_checksum(self.drivers_home / file_name),
                ],
            )
        )
        self.drivers_state.write()
        self.logger.debug(f"Driver {driver_type} added to ini file")

    def _delete_driver_files(self, filename: Path) -> None:
        """
        Delete WebDriver file

        :param filename: Name of the WebDriver file
        :return: None
        """
        filepath = self.drivers_home / filename
        if filepath.is_file():
            os.remove(str(filepath))
            self.logger.debug(f"Driver file deleted: {filename}")
        else:
            self.logger.debug(f"Driver file not found: {filename}")

    @staticmethod
    def __unpack_gz(arc_path: Path, dst_dir: Path) -> None:
        """
        Unpack gzipped archive to given path

        :param arc_path: Path to gzipped archive
        :param dst_dir: Where the archive will be unpacked
        :return: None
        """
        with gzip.open(arc_path, "rb") as gz:
            content = gz.read()
        with open(Path(dst_dir) / Path(arc_path).name.replace(".gz", ""), "wb") as f:
            f.write(content)

    def _unpack(self, archive_path: Path, working_dir: str) -> None:
        """
        Unpack any supported archive type

        :param archive_path: Path to an archive
        :param working_dir: Where the archive will be unpacked
        :return: None
        """
        compression_formats = [format_[0] for format_ in shutil.get_unpack_formats()]
        if "gz" not in compression_formats:
            shutil.register_unpack_format("gz", ["gz"], WebDriver.__unpack_gz)
        shutil.unpack_archive(archive_path, extract_dir=working_dir)
        self.logger.debug(f"Uncompressed {archive_path} to {self.drivers_home}")

    def install_driver(self, driver_type: str, url: str, version: str, os_: str, arch: str, file_name: Path) -> None:
        """
        Install given WebDriver version for given OS, architecture.

        Installation consists of following steps:
        * downloading driver archive
        * updating info about driver in .ini file

        :param driver_type: Type of the WebDriver e.g. chrome
        :param url: URL of the WebDriver type
        :param version: Version of the installed WebDriver
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :param file_name: Name of the WebDriver file
        :return: None
        """
        version_cache_dir = self.cache_dir / Path(driver_type) / Path(version)
        zipfile_path = version_cache_dir / file_name
        if not (version_cache_dir / file_name).is_file():
            self.logger.info("Requested driver not found in cache")
            self.support.setup_dirs([version_cache_dir])
            self._downloader.dl_driver(url, zipfile_path)
        else:
            self.logger.debug(f"{driver_type}driver in cache")
        self.replace_driver_and_update_ini(zipfile_path, driver_type, os_, arch, version)
        self.logger.info(f"Installed {driver_type}driver:\nVERSION: {version}\nOS: {os_}\nARCHITECTURE: {arch}")

    def update_version_dict(self, version: str, os_: str, arch: str, file_name: str) -> None:
        """
        Update information about installed, removed, updated driver in .ini file

        :param version: Version of the installed WebDriver
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :param file_name: Name of the WebDriver file
        :return: None
        """
        if version not in self._versions_info:
            self._versions_info[version] = {os_: {arch: file_name}}
        else:
            if os_ not in self._versions_info[version]:
                self._versions_info[version][os_] = {arch: file_name}
            else:
                self._versions_info[version][os_][arch] = file_name

    def print_drivers_from_ini(self) -> None:
        """
        Print in console information about installed drivers

        :return: None
        """
        if not self._drivers_cfg.exists() or len(self.drivers_state.sections) == 0:
            self.support.exit("No drivers installed")
        values = []
        for driver_type in self.drivers_state.sections:
            values.append([driver_type] + [self.drivers_state[driver_type][v] for v in WebDriver._CONFIG_KEYS[1:]])
        self.logger.info(tabulate.tabulate(values, headers=WebDriver._CONFIG_KEYS, showindex=True))

    def print_remote_drivers(self) -> None:
        """
        Print in console information about available to install WebDrivers

        :return: None
        """
        values = []
        for version, version_data in self._versions_info.items():
            for os_, os_data in version_data.items():
                values.append([version, os_, " ".join(os_data.keys())])
        values = sorted(values, key=lambda val: LooseVersion(val[0]))
        self.logger.info(tabulate.tabulate(values, headers=WebDriver._CONFIG_KEYS[1:4], showindex=True))

    def get_newest_version(self) -> str:
        """
        Return highest version of WebDriver.

        Only semantic versioning is supported.

        :return: Newest version of the driver as string
        """
        highest_v = str(sorted(self._versions_info.keys(), key=LooseVersion)[-1])
        self.logger.debug(f"Highest version of driver is: {highest_v}")
        return highest_v

    def validate_version_os_arch(
        self, driver_type: str, version: str, os_: str, arch: str
    ) -> Tuple[str, str, str, Path]:
        """
        Validate that requested version, OS and architecture of given WebDriver is available to install.

        If the OS or architecture were not given then get current platform values. If version was not given
        then get newest available version.

        :param driver_type: Type of the WebDriver e.g. chrome
        :param version: Version of the installed WebDriver
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :return: version, os, architecture, WebDriver file name
        """
        errors = []
        version = version or self.get_newest_version()
        os_ = os_ or self.system_name
        arch = arch or self.system_arch
        if driver_type == "gecko" and os_ == "mac":
            arch = ""  # gecko does not have arch for mac
        self.logger.debug(f"I will download following version: {version}, OS: {os_}, arch: {arch}")
        driver = self.drivers_state.get(driver_type)
        if driver:
            if os_ == driver.get("OS") and arch == driver.get("ARCHITECTURE") and version == driver.get("VERSION"):
                self.logger.info("Requested driver already installed")
                self.support.exit(exit_code=0)
        if version not in self._versions_info:
            errors.append(f"There is no such version: {version} of {driver_type}driver")
        else:
            if os_ not in self._versions_info[version]:
                errors.append(f"There is no such OS {os_} for version: {version}")
            else:
                if arch not in self._versions_info[version][os_]:
                    errors.append(f"There is no such arch {arch} for version {version} and OS: {os_}")
        if errors:
            self.support.exit(errors)
        return version, os_, arch, Path(self._versions_info[version][os_][arch])

    def clear_cache(self) -> None:
        """
        Delete cache directory

        :return: None
        """
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def replace_driver_and_update_ini(
        self,
        archive_path: Path,
        driver_type: str,
        os_: str,
        arch: str,
        version: str,
    ) -> None:
        """
        Put WebDriver file in installation dir and add/amend info in .ini file.

        If WebDriver file exists firstly delete it. File is extracted from archive downloaded from project's www.

        :param archive_path: Path to an archive with WebDriver
        :param driver_type: Type of the WebDriver e.g. chrome, gecko
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :param version: Version of the installed WebDriver
        :return: None
        """
        if driver_type in self.drivers_state.sections:
            old_driver_name = self.drivers_state[driver_type]["FILENAME"]
            self._delete_driver_files(old_driver_name)
        with tempfile.TemporaryDirectory() as tmpdir:
            self._unpack(archive_path, tmpdir)
            uncompressed_all_paths = list(Path(tmpdir).rglob("*"))  # get all paths with any nested folders
            all_driver_filenames = "|".join(WebDriverType.list_all_file_names())
            uncompressed_driver_paths = [
                file_path
                for file_path in uncompressed_all_paths
                if re.match(f".*({all_driver_filenames}).*", str(file_path.name))
            ]  # leaves only paths with driver name inside
            src = [path_ for path_ in uncompressed_driver_paths if path_.is_file()][0]  # get path of driver file
            uncompressed_file = Path(src.name)
            dst = self.drivers_home / uncompressed_file
            shutil.copyfile(src, dst)

        self._add_driver_to_ini(uncompressed_file, driver_type, os_, arch, version)

    def delete_drivers(self, driver_types_to_delete: Drivers) -> None:
        """
        Delete WebDriver file and update .ini file

        :param driver_types_to_delete: List of WebDriver types to be deleted
        :return: None
        """
        if not self._drivers_cfg.exists():
            self.support.exit("No drivers installed")
        if len(driver_types_to_delete) == 0:
            driver_types_to_delete = self.drivers_state.sections.copy()
        for driver_type in driver_types_to_delete:
            if driver_type not in self.drivers_state.sections:
                self.logger.info(f"Driver: {driver_type} is not installed")
            else:
                driver_filename = self.drivers_state[driver_type]["FILENAME"]
                self.drivers_state.pop(driver_type)
                self.logger.debug(f"Driver {driver_type} removed from ini")
                self._delete_driver_files(driver_filename)
                self.logger.info(f"Driver: {driver_type} deleted")
                self.drivers_state.write()

    def generic_update(
        self, driver_type: str, fn_get_remote_drivers_list: FnRemoteDriversList, fn_install: FnInstall
    ) -> None:
        """
        Replace currently installed version of any WebDriver with newest available.

        Generic method that handles all available WebDrivers due to ability to get as parameter methods specific
        for given drivers.

        :param driver_type: Type of the WebDriver e.g. chrome, gecko
        :param fn_get_remote_drivers_list: Method `get_remote_drivers_list` for given WebDriver (from its class)
        :param fn_install: Method `install` for given WebDriver (from its class)
        """
        self.logger.debug(f"Updating {driver_type}driver")
        driver_state = self.drivers_state.get(driver_type)
        if not driver_state:
            self.logger.info(f"Driver {driver_type}driver is not installed")
            return
        local_version = driver_state.get("VERSION")
        if not local_version:
            self.logger.info("Corrupted .ini file")
            return
        fn_get_remote_drivers_list()
        remote_version = self.get_newest_version()
        if LooseVersion(local_version) >= LooseVersion(remote_version):
            self.logger.info(
                f"{driver_type}driver is already in newest version. "
                f"Local: {local_version}, remote: {remote_version}"
            )
        else:
            os_ = self.drivers_state.get(driver_type, {}).get("OS")
            arch = self.drivers_state.get(driver_type, {}).get("ARCHITECTURE")
            fn_install(remote_version, os_, arch)
            self.logger.info(f"Updated {driver_type}driver: {local_version} -> {remote_version}")

    def get_remote_drivers_list(self) -> None:
        """
        Get available versions of WebDrivers together with supported OS and architece

        :return: None
        """
        raise NotImplementedError

    def install(self, version: str, os_: str, arch: str) -> None:
        """
        Install WebDriver

        :param version: Version of the installed WebDriver
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :return: None
        """
        raise NotImplementedError

    def update(self) -> None:
        """
        Replace currently installed version of chromedriver with newest available

        :return: None
        """
        raise NotImplementedError
