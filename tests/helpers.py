from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Tuple

from configobj import ConfigObj

from pydriver.config import WebDriverType
from pydriver.pydriver_types import OptionalString, PytestTmpDir

DRIVERS_OTHER_FILES = {
    "chrome": [],
    "gecko": [],
    "opera": ["sha512_sum"],
    "edge": [],
}

URLS = {
    "GECKO": "https://github.com/mozilla/geckodriver/releases/download/v{version}/{name}",
    "GECKO_API": "https://api.github.com/repos/mozilla/geckodriver/releases",
    "OPERA": "https://github.com/operasoftware/operachromiumdriver/releases/download/v.{version}/{name}",
    "OPERA_API": "https://api.github.com/repos/operasoftware/operachromiumdriver/releases",
    "CHROME": "https://chromedriver.storage.googleapis.com",
    "EDGE": "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver/{version}/{name}",
    "EDGE_API": "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver/?comp=list",
}
NOT_SUPPORTED = "not_supported"
PYDRIVER_HOME = "pydriver_home"
CACHE_DIR = ".pydriver_cache"
EXPECTED = {
    "CHROME": """    VERSION       OS     ARCHITECTURE
--  ------------  -----  --------------
 0  2.0           linux  32 64
 1  2.0           mac    32
 2  2.0           win    32
 3  2.1           linux  32 64
 4  2.1           mac    32
 5  71.0.3578.33  linux  64
 6  71.0.3578.33  mac    64
 7  71.0.3578.33  win    32""",
    "GECKO": """    VERSION    OS     ARCHITECTURE
--  ---------  -----  --------------
 0  0.4.2      linux  64
 1  0.4.2      mac
 2  0.4.2      win
 3  0.8.0      linux  64
 4  0.8.0      mac
 5  0.8.0      win    32
 6  0.16.1     arm    7hf
 7  0.16.1     linux  64
 8  0.16.1     mac
 9  0.16.1     win    32 64
10  0.28.0     linux  32 64
11  0.28.0     mac
12  0.28.0     win    32 64""",
    "OPERA": """    VERSION        OS     ARCHITECTURE
--  -------------  -----  --------------
 0  0.1.0          linux  32 64
 1  0.1.0          mac    32 64
 2  0.1.0          win    32
 3  0.2.0          linux  32 64
 4  0.2.0          mac    64
 5  0.2.0          win    32
 6  2.42           linux  64
 7  2.42           mac    64
 8  2.42           win    32 64
 9  2.45           linux  64
10  2.45           mac    64
11  2.45           win    32 64
12  87.0.4280.67   linux  64
13  87.0.4280.67   mac    64
14  87.0.4280.67   win    32 64
15  88.0.4324.104  linux  64
16  88.0.4324.104  mac    64
17  88.0.4324.104  win    32 64""",
    "EDGE": """    VERSION      OS     ARCHITECTURE
--  -----------  -----  --------------
 0  75.0.139.20  mac    64
 1  75.0.139.20  win    32 64
 2  76.0.159.0   mac    64
 3  76.0.159.0   win    32 64
 4  76.0.162.0   mac    64
 5  76.0.162.0   win    32 64
 6  76.0.165.0   win    86
 7  90.0.817.0   arm    64
 8  90.0.817.0   mac    64
 9  90.0.817.0   win    32 64
10  90.0.818.0   arm    64
11  90.0.818.0   linux  64
12  90.0.818.0   mac    64
13  90.0.818.0   win    32 64""",
}


class PlatformUname:
    """Provide system and machine strings for mocking `platform.uname` method"""

    def __init__(self, system="Windows", machine="AMD64"):
        self.system = system
        self.machine = machine


class IniFile:
    """Provide fluent API for creating `.drivers.ini` file"""

    def __init__(self):
        self.conf_obj = ConfigObj()

    def add_driver(self, driver_type: str, filename: str, version: str, os_: str, arch: str, checksum: str) -> IniFile:
        """
        Add new driver info to `.drivers.ini` file. Call `write` to save to file.

        :param driver_type: Type of the WebDriver i.e. chrome, gecko, opera, edge
        :param filename: Name of the WebDriver file
        :param version: Version of the installed WebDriver
        :param os_: OS for which WebDriver is installed
        :param arch: OS'es architecture for which WebDriver is installed
        :param checksum: Checksum od the filename
        :return: IniFile Class
        """
        self.conf_obj[driver_type] = {"OS": os_, "ARCHITECTURE": arch, "FILENAME": filename, "CHECKSUM": checksum}
        if version:
            self.conf_obj[driver_type].update({"VERSION": version})
        return self

    def write(self, directory: str) -> None:
        """
        Write to disk ConfObject created using `add_driver` method.

        :param directory: Path to directory where .drivers.ini file will be created
        :return: None
        """
        self.conf_obj.filename = os.path.join(directory, PYDRIVER_HOME, ".drivers.ini")
        self.conf_obj.write()

    def to_dict(self) -> Dict:
        """
        Return ConfObject as python dictionary.

        :return: Content of `.drivers.ini` file as dictionary
        """
        return self.conf_obj.dict()


@dataclass
class DriverData:
    """Hold information about the driver"""

    type: str = field(default="")
    version: str = field(default="")
    os_: str = field(default="")
    arch: str = field(default="")
    filename: str = field(default="")
    arc_filename: str = field(default="")


def create_unarc_driver(dst_dir: str, file_name: str) -> str:
    """
    Create driver file in given directory. Content of the file is 10 times `file_name`.

    :param dst_dir: Directory where to create a driver file
    :param file_name: Name of the driver file
    :return: Checksum of created driver file
    """
    content = 10 * file_name
    with open(os.path.join(dst_dir, file_name), "w") as f:
        f.write(content)
    return hashlib.md5(content.encode()).hexdigest()


def create_unarc_driver_other_files(dst_dir: str, driver_type: str) -> None:
    """
    Create other drivers file that are present in driver arc file

    :param dst_dir: Path where files are created
    :param driver_type: Type of WebDriver e.g. chrome, gecko, opera
    :return: None
    """
    for file_name in DRIVERS_OTHER_FILES[driver_type]:
        create_unarc_driver(dst_dir, file_name)


def create_arc_driver(
    tmp_dir: str,
    driver_type: str,
    arc_file_name: str,
    unarc_file_name: str,
    cache_dir: OptionalString = None,
    version: OptionalString = None,
) -> str:
    """
    Create archive of given type with driver file and other files (like checksums) inside.

    :param tmp_dir: Path to pytest `tmpdir`
    :param driver_type: Type of WebDriver e.g. chrome, gecko, opera
    :param arc_file_name: Name of the archive file to be created with extension
    :param unarc_file_name: Name of the webdriver file
    :param cache_dir: Name of the pydriver cache directory (default: None)
    :param version: Version of the installed WebDriver (default: None)
    :return: Checksum of created driver file (not compressed)
    """
    if cache_dir is None:
        cache_dir = os.path.join(tmp_dir, CACHE_DIR, driver_type, version)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        nested_folder = tmp
        if driver_type == WebDriverType.OPERA.drv_name:
            nested_folder = os.path.join(tmp, os.path.splitext(arc_file_name)[0])
            os.makedirs(nested_folder)
        checksum = create_unarc_driver(nested_folder, unarc_file_name)
        create_unarc_driver_other_files(nested_folder, driver_type)

        if arc_file_name.endswith(".tar.gz"):
            file_name = arc_file_name.replace(".tar.gz", "")
            dst = os.path.join(cache_dir, file_name)
            shutil.make_archive(dst, "gztar", tmp)
        elif arc_file_name.endswith(".zip"):
            file_name = arc_file_name.replace(".zip", "")
            dst = os.path.join(cache_dir, file_name)
            shutil.make_archive(dst, "zip", tmp)
        elif arc_file_name.endswith(".gz"):
            dst = os.path.join(cache_dir, arc_file_name)
            with open(os.path.join(tmp, unarc_file_name), "rb") as f_in:
                with gzip.open(dst, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
    return checksum


def load_driver_arc_content(tmp_dir: str, driver_type: str, arc_file_name: str, unarc_file_name: str) -> Tuple:
    """
    Create archive file and returns it as string and checksum of the created webdriver file

    :param tmp_dir: Path to pytest `tmpdir`
    :param driver_type: Type of WebDriver e.g. chrome, gecko, opera
    :param arc_file_name: Name of the archive file to be created with extension
    :param unarc_file_name: Name of the webdriver file
    :return: Tuple with archive as string and checksum of the webdriver file
    """
    checksum = create_arc_driver(tmp_dir, driver_type, arc_file_name, unarc_file_name, cache_dir=tmp_dir)
    arc_driver_path = tmp_dir.join(arc_file_name)
    with open(arc_driver_path, "rb") as f:
        content = f.read()
    return content, checksum


def get_ini_content(tmp_dir: PytestTmpDir) -> Dict:
    """
    Return content of the drivers.ini file

    :param tmp_dir: Path to pytest `tmpdir`
    :return: Content of `.drivers.ini` as dictionary
    """
    return ConfigObj(tmp_dir.join(PYDRIVER_HOME, ".drivers.ini")).dict()


def load_response(driver_type: str) -> Dict[str, str]:
    """
    Get from resources directory recorder response of webserver with list of available webdrivers

    :param driver_type: Type of WebDriver e.g. chrome, gecko
    :return: Dictionary with content type as key and content of the file as value
    """
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", f"{driver_type}.txt")
    with open(resource_path) as f:
        content = f.read()
    if driver_type in ["gecko", "opera"]:
        return {"json": json.loads(content)}
    return {"text": content}
