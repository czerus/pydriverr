import gzip
import hashlib
import json
import logging
import os
import platform
import shutil
import tempfile
from typing import Dict

import py
import pytest
from click.testing import CliRunner
from configobj import ConfigObj

from pydriver import pydriver, webdriver
from pydriver.config import WebDriverType
from pydriver.pydriver import cli_pydriver
from tests.fixtures import assert_in_log, assert_not_in_log

PytestTmpDir = py.path.local

GECKO_URL = "https://github.com/mozilla/geckodriver"
OPERA_URL = "https://github.com/operasoftware/operachromiumdriver"
GECKO_API_URL = "https://api.github.com/repos/mozilla/geckodriver"
OPERA_API_URL = "https://api.github.com/repos/operasoftware/operachromiumdriver"
CHROME_URL = "https://chromedriver.storage.googleapis.com"
EDGE_URL = "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver"
EDGE_API_URL = "https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver/?comp=list"
NOT_SUPPORTED = "not_supported"
PYDRIVER_HOME = "pydriver_home"
CACHE_DIR = ".pydriver_cache"
EXPECTED_CHROME = """    VERSION       OS     ARCHITECTURE
--  ------------  -----  --------------
 0  2.0           linux  32 64
 1  2.0           mac    32
 2  2.0           win    32
 3  2.1           linux  32 64
 4  2.1           mac    32
 5  71.0.3578.33  linux  64
 6  71.0.3578.33  mac    64
 7  71.0.3578.33  win    32"""
EXPECTED_GECKO = """    VERSION    OS     ARCHITECTURE
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
12  0.28.0     win    32 64"""
EXPECTED_OPERA = """    VERSION        OS     ARCHITECTURE
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
17  88.0.4324.104  win    32 64"""
EXPECTED_EDGE = """    VERSION      OS     ARCHITECTURE
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
13  90.0.818.0   win    32 64"""
# TODO: possibly replace DRIVERS_CFG with small dicts anc create_custom_ini
DRIVERS_CFG = {
    "chrome": [
        {
            "VERSION": "81.0.4044.20",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "chromedriver.exe",
            "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
            "IN_INI": True,
        },
        {
            "VERSION": "81.0.4044.20",
            "OS": "linux",
            "ARCHITECTURE": "32",
            "FILENAME": "chromedriver",
            "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
        },
        {
            "VERSION": "81.0.4044.20",
            "OS": "mac",
            "ARCHITECTURE": "64",
            "FILENAME": "chromedriver",
            "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
        },
    ],
    "gecko": [
        {
            "VERSION": "0.28.0",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "geckodriver.exe",
            "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
            "IN_INI": True,
        }
    ],
    "opera": [
        {
            "VERSION": "88.0.4324.104",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "operadriver.exe",
            "CHECKSUM": "c6847807558142bec4e1bcc70ffa2387",
            "IN_INI": True,
        },
        {
            "VERSION": "88.0.4324.104",
            "OS": "linux",
            "ARCHITECTURE": "64",
            "FILENAME": "operadriver",
            "CHECKSUM": "82250dc9c5224fa2d012e5b60300c96b",
        },
        {
            "VERSION": "88.0.4324.104",
            "OS": "mac",
            "ARCHITECTURE": "64",
            "FILENAME": "operadriver",
            "CHECKSUM": "e06c3da38cc9d4fdd92a8967707f9c79",
        },
        {
            "VERSION": "0.1.1",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "operadriver.exe",
            "CHECKSUM": "96ef9b54ebd1240fdf96bfec97fdac93",
        },
    ],
    "edge": [
        {
            "VERSION": "90.0.818.0",
            "OS": "arm",
            "ARCHITECTURE": "64",
            "FILENAME": "msedgedriver.exe",
            "CHECKSUM": "52f75e24f36f52725675542a179b1d68",
        },
        {
            "VERSION": "90.0.818.0",
            "OS": "linux",
            "ARCHITECTURE": "64",
            "FILENAME": "msedgedriver",
            "CHECKSUM": "b91ecc20d0108f0a60d35c827cd9e384",
        },
        {
            "VERSION": "90.0.818.0",
            "OS": "mac",
            "ARCHITECTURE": "64",
            "FILENAME": "msedgedriver",
            "CHECKSUM": "925f0d868bed41382a97d1fd39742b34",
        },
        {
            "VERSION": "90.0.818.0",
            "OS": "win",
            "ARCHITECTURE": "64",
            "FILENAME": "msedgedriver.exe",
            "CHECKSUM": "648d1e0bc42a563fe92496efcad85bd9",
        },
        {
            "VERSION": "90.0.818.0",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "msedgedriver.exe",
            "CHECKSUM": "46920536a8723dc0a68dedc3bb0f0fba",
            "IN_INI": True,
        },
    ],
}

DRIVERS_OTHER_FILES = {
    "chrome": [],
    "gecko": [],
    "opera": ["sha512_sum"],
    "edge": [],
}


def create_unarc_driver(dst_dir: str, file_name: str) -> str:
    content = 10 * file_name
    with open(os.path.join(dst_dir, file_name), "w") as f:
        f.write(content)
    return hashlib.md5(content.encode()).hexdigest()


def create_unarc_driver_other_files(dst_dir: str, driver_type: str) -> None:
    """
    Create other drivers file that are present in driver arc file

    :param dst_dir: Path where files are created
    :param driver_type: Type of WebDriver e.g. chrome, gecko, opera
    """
    for file_name in DRIVERS_OTHER_FILES[driver_type]:
        create_unarc_driver(dst_dir, file_name)


def create_arc_driver(tmp_dir, driver_type, arc_file_name, unarc_file_name, cache_dir=None, version=None) -> str:
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


def load_driver_arc_content(tmp_dir, driver_type, arc_file_name, unarc_file_name):
    checksum = create_arc_driver(tmp_dir, driver_type, arc_file_name, unarc_file_name, cache_dir=tmp_dir)
    arc_driver_path = tmp_dir.join(arc_file_name)
    with open(arc_driver_path, "rb") as f:
        content = f.read()
    return content, checksum


def get_installed_driver_from_ini(driver_type: str) -> Dict:
    """Removes from ini driver_type and all keys without IN_INI: True"""
    new_cfg = {}
    for key, val in DRIVERS_CFG.items():
        driver_in_ini = [drv for drv in val if drv.get("IN_INI")][0]
        if key != driver_type:
            # Make sure that all values are strings, especially IN_INI
            new_cfg[key] = {k: str(v) for (k, v) in driver_in_ini.items()}
    return new_cfg


@pytest.fixture
def test_dirs(tmpdir):
    tmpdir.mkdir(PYDRIVER_HOME)
    tmpdir.mkdir(CACHE_DIR)


@pytest.fixture
def create_ini(tmpdir):
    conf_obj = ConfigObj()
    conf_obj.filename = tmpdir.join(PYDRIVER_HOME, ".drivers.ini")
    for driver_type, cached_drivers in DRIVERS_CFG.items():
        for driver in cached_drivers:
            if driver.get("IN_INI"):
                conf_obj[driver_type] = driver
    conf_obj.write()


def create_custom_ini(tmp_dir, driver_type, filename, version, os_, arch, checksum):
    """Create pydriver.ini file with requested content

    :param tmp_dir: Path where ini should be created
    :param driver_type: Type of WebDriver e.g. chrome, gecko
    :param filename: File name of the WebDriver e.g. chromedriver or geckodriver.exe
    :param version: WebDriver version
    :param os_: Operating system i.e. win, linux, mac
    :param arch: Architecture of the OS e.g. 64, 32
    :param checksum: MD5 checksum of WebDriver file
    """
    conf_obj = ConfigObj()
    conf_obj.filename = tmp_dir.join(PYDRIVER_HOME, ".drivers.ini")
    conf_obj[driver_type] = {"OS": os_, "ARCHITECTURE": arch, "FILENAME": filename, "CHECKSUM": checksum}
    if version:
        conf_obj[driver_type].update({"VERSION": version})
    conf_obj.write()


@pytest.fixture
def empty_ini(tmpdir):
    with open(os.path.join(tmpdir, PYDRIVER_HOME, ".drivers.ini"), "w") as f:
        f.write("\n\n")


@pytest.fixture
def env_vars(monkeypatch, tmpdir):
    monkeypatch.setenv(webdriver.WebDriver._ENV_NAME, str(tmpdir.join(PYDRIVER_HOME)))
    system = platform.system().lower()
    if system == "windows":
        monkeypatch.setenv("USERPROFILE", str(tmpdir))
    elif system in ["linux", "darwin"]:
        monkeypatch.setenv("HOME", str(tmpdir))
    else:
        raise Exception(f"Unsupported system: {system}")


def load_response(driver_type: str):
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", f"{driver_type}.txt")
    with open(resource_path) as f:
        content = f.read()
    if driver_type in ["gecko", "opera"]:
        return json.loads(content)
    return content


def get_ini_content(work_dir: PytestTmpDir) -> Dict:
    """Return content of the drivers.ini file"""
    return dict(ConfigObj(work_dir.join(PYDRIVER_HOME, ".drivers.ini")))


class PlatformUname:
    def __init__(self, system="Windows", machine="AMD64"):
        self.system = system
        self.machine = machine


class TestWebdriverSystemIdentification:
    """Use WebDriver class in order to test underlying system identification"""

    @pytest.mark.parametrize(
        "user_input,expected",
        [(PlatformUname("Windows"), "win"), (PlatformUname("Darwin"), "mac"), (PlatformUname("Linux"), "linux")],
    )
    def test_system_name(self, user_input, expected, env_vars, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = user_input
        driver = webdriver.WebDriver()
        webdriver.platform.uname.assert_called()
        assert driver.system_name == expected
        assert f"Current's OS type string: {user_input.system.lower()} -> {expected}" in caplog.text

    def test_system_name_nok(self, env_vars, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname(system="nok")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        webdriver.platform.uname.assert_called()
        assert "Unknown OS type: nok" in caplog.text

    @pytest.mark.parametrize(
        "user_input,expected",
        [
            (PlatformUname(machine="x86_64"), "64"),
            (PlatformUname(machine="AMD64"), "64"),
            (PlatformUname(machine="i386"), "32"),
            (PlatformUname(machine="i586"), "32"),
        ],
    )
    def test_machine(self, user_input, expected, env_vars, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = user_input
        driver = webdriver.WebDriver()
        webdriver.platform.uname.assert_called()
        assert driver.system_arch == expected
        assert f"Current's OS architecture string: {user_input.machine} -> {expected} bit" in caplog.text

    def test_machine_nok(self, env_vars, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname(machine="nok")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        webdriver.platform.uname.assert_called()
        assert "Unknown architecture: nok" in caplog.text

    def test__get_drivers_home(self, env_vars, tmpdir, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        webdriver.WebDriver()
        assert f"{webdriver.WebDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.text

    def test__get_drivers_home_nok(self, caplog, mocker, monkeypatch):
        """ Test missing path in DRIVERS_HOME env."""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        monkeypatch.setenv(webdriver.WebDriver._ENV_NAME, "")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        assert f"Env variable '{webdriver.WebDriver._ENV_NAME}' not defined" in caplog.text

    def test_printed_logs(self, env_vars, tmpdir, caplog, mocker):
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        webdriver.WebDriver()
        assert "Current's OS architecture string: AMD64 -> 64 bit" in caplog.text
        assert "Current's OS type string: windows -> win" in caplog.text
        assert f"{webdriver.WebDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.text
        assert "Identified OS: win" in caplog.text
        assert "Identified architecture: 64" in caplog.text


class TestShowEnv:
    def test_show_env_empty_empty(self, env_vars, caplog, tmpdir, test_dirs, mocker):
        runner = CliRunner()
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        result = runner.invoke(cli_pydriver, ["show-env"])
        assert result.exit_code == 0
        assert_in_log(
            caplog.messages, f"WebDrivers are installed in: {tmpdir.join(PYDRIVER_HOME)}, total size is: 0 bytes"
        )
        assert_in_log(caplog.messages, f"PyDriver cache is in: {tmpdir.join(CACHE_DIR)}, total size is: 0 bytes")

    def test_show_env_empty_with_files(self, env_vars, caplog, tmpdir, test_dirs, create_ini, mocker):
        runner = CliRunner()
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        mocker.patch("pydriver.support.humanfriendly.format_size").side_effect = ["365 bytes", "1.69 KB"]
        result = runner.invoke(cli_pydriver, ["show-env"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"PyDriver cache is in: {tmpdir.join(CACHE_DIR)}, total size is: 1.69 KB")
        assert_in_log(
            caplog.messages, f"WebDrivers are installed in: {tmpdir.join(PYDRIVER_HOME)}, total size is: 365 bytes"
        )


class TestInstalledDrivers:
    def test_installed_drivers_empty_ini(self, env_vars, tmpdir, test_dirs, empty_ini, mocker, caplog):
        runner = CliRunner()
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        result = runner.invoke(cli_pydriver, ["show-installed"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, "No drivers installed")

    def test_installed_drivers_driver_home_does_not_exist(self, env_vars, tmpdir, mocker, caplog):
        runner = CliRunner()
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        mocker.patch("pydriver.support.Path.mkdir")
        result = runner.invoke(cli_pydriver, ["show-installed"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, f"{tmpdir.join(PYDRIVER_HOME)} directory does not exist")

    def test_installed_drivers_installed(self, env_vars, tmpdir, test_dirs, create_ini, caplog, mocker):
        expected = """    DRIVER TYPE    VERSION        OS      ARCHITECTURE  FILENAME          CHECKSUM
--  -------------  -------------  ----  --------------  ----------------  --------------------------------
 0  chrome         81.0.4044.20   win               32  chromedriver.exe  56db17c16d7fc9003694a2a01e37dc87
 1  gecko          0.28.0         win               32  geckodriver.exe   56db17c16d7fc9003694a2a01e37dc87
 2  opera          88.0.4324.104  win               32  operadriver.exe   c6847807558142bec4e1bcc70ffa2387
 3  edge           90.0.818.0     win               32  msedgedriver.exe  46920536a8723dc0a68dedc3bb0f0fba"""
        runner = CliRunner()
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        result = runner.invoke(cli_pydriver, ["show-installed"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, expected)


class TestListDrivers:
    @pytest.mark.parametrize(
        "driver_type, url, expected_printout, request_kwargs",
        [
            (
                "chrome",
                "https://chromedriver.storage.googleapis.com",
                EXPECTED_CHROME,
                {"text": load_response("chrome")},
            ),
            (
                "gecko",
                "https://api.github.com/repos/mozilla/geckodriver/releases",
                EXPECTED_GECKO,
                {"json": load_response("gecko")},
            ),
            (
                "opera",
                f"{OPERA_API_URL}/releases",
                EXPECTED_OPERA,
                {"json": load_response("opera")},
            ),
            (
                "edge",
                f"{EDGE_API_URL}",
                EXPECTED_EDGE,
                {"text": load_response("edge")},
            ),
        ],
    )
    def test_list_drivers(
        self, driver_type, url, expected_printout, request_kwargs, tmpdir, env_vars, caplog, requests_mock
    ):
        runner = CliRunner()
        requests_mock.get(url, **request_kwargs)
        result = runner.invoke(cli_pydriver, ["show-available", "-d", driver_type])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, expected_printout)

    def test_list_drivers_not_supported_driver(self, env_vars, caplog):
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["show-available", "-d", NOT_SUPPORTED])
        assert result.exit_code == 2
        assert result.exc_info[0] == SystemExit

    def test_list_drivers_network_error(self, env_vars, tmpdir, caplog, requests_mock):
        runner = CliRunner()
        requests_mock.get(CHROME_URL, status_code=404)
        result = runner.invoke(cli_pydriver, ["show-available", "-d", "chrome"])
        assert result.exc_info[0] == SystemExit
        assert result.exit_code == 1
        assert_in_log(caplog.messages, f"Cannot download file {CHROME_URL}")


class TestDeleteDriver:
    def test_delete_driver_no_drivers_installed(self, tmpdir, env_vars, caplog):
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["delete", "-d", "chrome"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, "No drivers installed")

    def test_delete_driver_driver_not_installed(self, tmpdir, test_dirs, env_vars, caplog, empty_ini):
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["delete", "-d", "chrome"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, "Driver: chrome is not installed")

    @pytest.mark.parametrize(
        "driver_type, driver_file",
        [
            ("chrome", "chromedriver.exe"),
            ("gecko", "geckodriver.exe"),
            ("opera", "operadriver.exe"),
            ("edge", "msedgedriver.exe"),
        ],
    )
    def test_delete_driver_single_driver(
        self, driver_type, driver_file, tmpdir, test_dirs, env_vars, caplog, create_ini
    ):
        runner = CliRunner()
        create_unarc_driver(tmpdir.join(PYDRIVER_HOME), driver_file)
        result = runner.invoke(cli_pydriver, ["delete"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Driver {driver_type} removed from ini")
        assert_in_log(caplog.messages, f"Driver file deleted: {driver_file}")
        assert_in_log(caplog.messages, f"Driver: {driver_type} deleted")
        assert get_ini_content(tmpdir) == {}

    def test_delete_driver_many_drivers(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        runner = CliRunner()
        all_drivers = {"chrome": "chromedriver.exe", "gecko": "geckodriver.exe", "opera": "operadriver.exe"}
        for driver_type, driver_file_name in all_drivers.items():
            create_unarc_driver(tmpdir.join(PYDRIVER_HOME), driver_file_name)
        result = runner.invoke(cli_pydriver, ["delete"])
        assert result.exit_code == 0
        for driver_type, driver_file_name in all_drivers.items():
            assert_in_log(caplog.messages, f"Driver {driver_type} removed from ini")
            assert_in_log(caplog.messages, f"Driver file deleted: {driver_file_name}")
            assert_in_log(caplog.messages, f"Driver: {driver_type} deleted")
        assert get_ini_content(tmpdir) == {}

    def test_delete_driver_file_does_not_exist(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["delete", "-d", "chrome"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, "Driver chrome removed from ini")
        assert_in_log(caplog.messages, "Driver file not found: chromedriver.exe")
        assert_in_log(caplog.messages, "Driver: chrome deleted")
        assert get_ini_content(tmpdir) == {
            "gecko": {
                "VERSION": "0.28.0",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": "geckodriver.exe",
                "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
                "IN_INI": "True",
            },
            "opera": {
                "VERSION": "88.0.4324.104",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": "operadriver.exe",
                "CHECKSUM": "c6847807558142bec4e1bcc70ffa2387",
                "IN_INI": "True",
            },
            "edge": {
                "VERSION": "90.0.818.0",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": "msedgedriver.exe",
                "CHECKSUM": "46920536a8723dc0a68dedc3bb0f0fba",
                "IN_INI": "True",
            },
        }


class TestInstallDriver:
    def test_install_driver_not_supported_driver(self, env_vars, caplog):
        runner = CliRunner()
        result = runner.invoke(
            cli_pydriver, ["install", "-d", NOT_SUPPORTED, "-v", "71.0.3578.33", "-o", "win", "-a", "32"]
        )
        assert result.exit_code == 2
        assert result.exc_info[0] == SystemExit

    @pytest.mark.parametrize(
        "driver_type, get_versions_args, get_file_args, version, unarc_file_name, arc_file_name, os_, arch",
        [
            (
                "chrome",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                {"url": f"{CHROME_URL}/" + "{version}/{name}"},
                "71.0.3578.33",
                "chromedriver.exe",
                "chromedriver_win32.zip",
                "win",
                "32",
            ),
            (
                "gecko",
                {"url": f"{GECKO_API_URL}/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.28.0",
                "geckodriver.exe",
                "geckodriver-v0.28.0-win32.zip",
                "win",
                "32",
            ),
            (
                "gecko",
                {"url": f"{GECKO_API_URL}/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.28.0",
                "geckodriver",
                "geckodriver-v0.28.0-linux64.tar.gz",
                "linux",
                "64",
            ),
            (
                "gecko",
                {"url": f"{GECKO_API_URL}/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.28.0",
                "geckodriver",
                "geckodriver-v0.28.0-macos.tar.gz",
                "mac",
                "",
            ),
            (
                "opera",
                {"url": f"{OPERA_API_URL}/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "88.0.4324.104",
                "operadriver.exe",
                "operadriver_win32.zip",
                "win",
                "32",
            ),
            (
                "opera",
                {"url": f"{OPERA_API_URL}/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "88.0.4324.104",
                "operadriver",
                "operadriver_linux64.zip",
                "linux",
                "64",
            ),
            (
                "opera",
                {"url": f"{OPERA_API_URL}/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "88.0.4324.104",
                "operadriver",
                "operadriver_mac64.zip",
                "mac",
                "64",
            ),
            (
                "edge",
                {"url": f"{EDGE_API_URL}", "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.818.0",
                "msedgedriver.exe",
                "edgedriver_win64.zip",
                "win",
                "64",
            ),
            (
                "edge",
                {"url": f"{EDGE_API_URL}", "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.818.0",
                "msedgedriver.exe",
                "edgedriver_arm64.zip",
                "arm",
                "64",
            ),
            (
                "edge",
                {"url": f"{EDGE_API_URL}", "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.818.0",
                "msedgedriver",
                "edgedriver_mac64.zip",
                "mac",
                "64",
            ),
        ],
    )
    def test_install_driver_newest_version_not_in_cache(
        self,
        driver_type,
        get_versions_args,
        get_file_args,
        version,
        arc_file_name,
        unarc_file_name,
        os_,
        arch,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        requests_mock.get(get_versions_args["url"], **get_versions_args["kwargs"])
        content, checksum = load_driver_arc_content(tmpdir, driver_type, arc_file_name, unarc_file_name)
        requests_mock.get(get_file_args["url"].format(version=version, name=arc_file_name), content=content)
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["install", "-d", driver_type, "-o", os_, "-a", arch])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Requested version: , OS: {os_}, arch: {arch}")
        assert_in_log(caplog.messages, f"Highest version of driver is: {version}")
        assert_in_log(caplog.messages, "Requested driver not found in cache")
        assert_in_log(caplog.messages, f"I will download following version: {version}, OS: {os_}, arch: {arch}")
        assert_in_log(
            caplog.messages, f"Installed {driver_type}driver:\nVERSION: {version}\n" f"OS: {os_}\nARCHITECTURE: {arch}"
        )
        assert get_ini_content(tmpdir) == {
            driver_type: {
                "VERSION": version,
                "OS": os_,
                "ARCHITECTURE": arch,
                "FILENAME": unarc_file_name,
                "CHECKSUM": checksum,
            }
        }

    @pytest.mark.parametrize(
        "driver_type, request_urls, version",
        [
            ("chrome", {CHROME_URL: {"text": load_response("chrome")}}, "71.0.3578.33"),
            ("gecko", {GECKO_API_URL + "/releases": {"json": load_response("gecko")}}, "0.28.0"),
            ("opera", {OPERA_API_URL + "/releases": {"json": load_response("opera")}}, "88.0.4324.104"),
            ("edge", {EDGE_API_URL: {"text": load_response("edge")}}, "90.0.818.0"),
        ],
    )
    def test_install_driver_invalid_os(
        self, driver_type, request_urls, version, tmpdir, test_dirs, env_vars, caplog, requests_mock
    ):
        runner = CliRunner()
        for url, request_kwargs in request_urls.items():
            requests_mock.get(url, **request_kwargs)
        result = runner.invoke(
            cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", NOT_SUPPORTED, "-a", "32"]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, f"There is no such OS {NOT_SUPPORTED} for version: {version}")

    @pytest.mark.parametrize(
        "driver_type, request_urls, version",
        [
            ("chrome", {CHROME_URL: {"text": load_response("chrome")}}, "1.1.1.1"),
            ("gecko", {GECKO_API_URL + "/releases": {"json": load_response("gecko")}}, "1.1.1.1"),
            ("opera", {OPERA_API_URL + "/releases": {"json": load_response("opera")}}, "1.1.1.1"),
            ("edge", {EDGE_API_URL: {"text": load_response("edge")}}, "1.1.1.1"),
        ],
    )
    def test_install_driver_invalid_version(
        self, driver_type, request_urls, version, tmpdir, test_dirs, env_vars, caplog, requests_mock
    ):
        runner = CliRunner()
        for url, request_kwargs in request_urls.items():
            requests_mock.get(url, **request_kwargs)
        result = runner.invoke(cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", "win", "-a", "32"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, f"There is no such version: {version}")

    @pytest.mark.parametrize(
        "driver_type, request_urls, version",
        [
            ("chrome", {CHROME_URL: {"text": load_response("chrome")}}, "71.0.3578.33"),
            ("gecko", {GECKO_API_URL + "/releases": {"json": load_response("gecko")}}, "0.28.0"),
            ("opera", {OPERA_API_URL + "/releases": {"json": load_response("opera")}}, "88.0.4324.104"),
            ("edge", {EDGE_API_URL: {"text": load_response("edge")}}, "90.0.818.0"),
        ],
    )
    def test_install_driver_invalid_arch(
        self, driver_type, request_urls, version, tmpdir, test_dirs, env_vars, caplog, requests_mock
    ):
        runner = CliRunner()
        for url, request_kwargs in request_urls.items():
            requests_mock.get(url, **request_kwargs)
        result = runner.invoke(
            cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", "win", "-a", NOT_SUPPORTED]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert_in_log(caplog.messages, f"There is no such arch {NOT_SUPPORTED} for version {version} and OS: win")

    @pytest.mark.parametrize(
        "driver_type, request_urls, version",
        [
            ("chrome", {CHROME_URL: {"text": load_response("chrome")}}, "81.0.4044.20"),
            ("gecko", {GECKO_API_URL + "/releases": {"json": load_response("gecko")}}, "0.28.0"),
            ("opera", {OPERA_API_URL + "/releases": {"json": load_response("opera")}}, "88.0.4324.104"),
            ("edge", {EDGE_API_URL: {"text": load_response("edge")}}, "90.0.818.0"),
        ],
    )
    def test_install_driver_already_installed(
        self, driver_type, request_urls, version, tmpdir, test_dirs, env_vars, caplog, create_ini, requests_mock
    ):
        runner = CliRunner()
        for url, request_kwargs in request_urls.items():
            requests_mock.get(url, **request_kwargs)
        result = runner.invoke(cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", "win", "-a", "32"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, "Requested driver already installed")

    @pytest.mark.parametrize(
        "driver_type, unarc_filename, arc_file_name, get_versions_args, get_file_args, version, os_, arch",
        [
            (
                "chrome",
                "chromedriver",
                "chromedriver_linux64.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                {"url": f"{CHROME_URL}/" + "{version}/{name}"},
                "71.0.3578.33",
                "linux",
                "64",
            ),
            (
                "chrome",
                "chromedriver",
                "chromedriver_mac64.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                {"url": f"{CHROME_URL}/" + "{version}/{name}"},
                "71.0.3578.33",
                "mac",
                "64",
            ),
            (
                "gecko",
                "geckodriver.exe",
                "geckodriver-v0.16.1-win64.zip",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.16.1",
                "win",
                "64",
            ),
            (
                "gecko",
                "geckodriver",
                "geckodriver-v0.16.1-linux64.tar.gz",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.16.1",
                "linux",
                "64",
            ),
            (
                "gecko",
                "wires-0.4.2-osx",
                "wires-0.4.2-osx.gz",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.4.2",
                "mac",
                "",
            ),
            (
                "opera",
                "operadriver.exe",
                "operadriver_win64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "87.0.4280.67",
                "win",
                "64",
            ),
            (
                "opera",
                "operadriver",
                "operadriver_linux64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "87.0.4280.67",
                "linux",
                "64",
            ),
            (
                "opera",
                "operadriver",
                "operadriver_mac64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "87.0.4280.67",
                "mac",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_win64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.817.0",
                "win",
                "64",
            ),
            (
                "edge",
                "msedgedriver",
                "edgedriver_mac64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.817.0",
                "mac",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_arm64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "90.0.817.0",
                "arm",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_win86.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "76.0.165.0",
                "win",
                "86",
            ),
        ],
    )
    def test_install_driver_replace_driver(
        self,
        driver_type,
        unarc_filename,
        arc_file_name,
        get_versions_args,
        get_file_args,
        version,
        os_,
        arch,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        create_ini,
        requests_mock,
    ):
        runner = CliRunner()
        content, calc_hash = load_driver_arc_content(tmpdir, driver_type, arc_file_name, unarc_filename)
        create_unarc_driver(tmpdir.join(PYDRIVER_HOME), unarc_filename)
        requests_mock.get(get_versions_args["url"], **get_versions_args["kwargs"])
        requests_mock.get(get_file_args["url"].format(version=version, name=arc_file_name), content=content)
        result = runner.invoke(cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", os_, "-a", arch])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Requested version: {version}, OS: {os_}, arch: {arch}")
        assert_in_log(
            caplog.messages, f"Installed {driver_type}driver:\nVERSION: {version}\nOS: {os_}\nARCHITECTURE: {arch}"
        )
        assert get_ini_content(tmpdir).get(driver_type, {}) == {
            "VERSION": version,
            "OS": os_,
            "ARCHITECTURE": arch,
            "FILENAME": unarc_filename,
            "CHECKSUM": calc_hash,
        }

    @pytest.mark.parametrize(
        "driver_type, unarc_filename, arc_file_name, request_urls, version, os_, arch",
        [
            (
                "chrome",
                "chromedriver",
                "chromedriver_linux64.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                "71.0.3578.33",
                "linux",
                "64",
            ),
            (
                "chrome",
                "chromedriver",
                "chromedriver_mac64.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                "71.0.3578.33",
                "mac",
                "64",
            ),
            (
                "gecko",
                "geckodriver.exe",
                "geckodriver-v0.28.0-win64.zip",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                "0.28.0",
                "win",
                "64",
            ),
            (
                "gecko",
                "wires-0.4.2-osx",
                "wires-0.4.2-osx.gz",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                "0.4.2",
                "mac",
                "",
            ),
            (
                "opera",
                "operadriver.exe",
                "operadriver_win64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                "87.0.4280.67",
                "win",
                "64",
            ),
            (
                "opera",
                "operadriver",
                "operadriver_linux64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                "0.1.0",
                "linux",
                "64",
            ),
            (
                "opera",
                "operadriver",
                "operadriver_mac64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                "87.0.4280.67",
                "mac",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_win64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                "90.0.818.0",
                "win",
                "64",
            ),
            (
                "edge",
                "msedgedriver",
                "edgedriver_mac64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                "90.0.818.0",
                "mac",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_arm64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                "90.0.818.0",
                "arm",
                "64",
            ),
        ],
    )
    def test_install_driver_from_cache(
        self,
        driver_type,
        unarc_filename,
        arc_file_name,
        request_urls,
        version,
        os_,
        arch,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        runner = CliRunner()
        requests_mock.get(request_urls["url"], **request_urls["kwargs"])
        checksum = create_arc_driver(tmpdir, driver_type, arc_file_name, unarc_filename, version=version)
        result = runner.invoke(cli_pydriver, ["install", "-d", driver_type, "-v", version, "-o", os_, "-a", arch])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Requested version: {version}, OS: {os_}, arch: {arch}")
        assert_in_log(caplog.messages, f"{driver_type}driver in cache")
        assert_in_log(
            caplog.messages, f"Installed {driver_type}driver:\nVERSION: {version}\nOS: {os_}\nARCHITECTURE: {arch}"
        )
        assert get_ini_content(tmpdir) == {
            driver_type: {
                "VERSION": version,
                "OS": os_,
                "ARCHITECTURE": arch,
                "FILENAME": unarc_filename,
                "CHECKSUM": checksum,
            }
        }


class TestClearCache:
    def test_clear_cache(self, env_vars, caplog, test_dirs, tmpdir):
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["clear-cache"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Removing cache directory: {tmpdir.join(CACHE_DIR)}")


class TestUpdate:
    @pytest.mark.parametrize(
        "driver_type, unarc_filename, arc_file_name, get_versions_args, get_file_args, version, new_version, os_, arch",
        [
            (
                "chrome",
                "chromedriver.exe",
                "chromedriver_win32.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                {"url": f"{CHROME_URL}/" + "{version}/{name}"},
                "2.0",
                "71.0.3578.33",
                "win",
                "32",
            ),
            (
                "gecko",
                "geckodriver",
                "geckodriver-v0.28.0-macos.tar.gz",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                {"url": f"{GECKO_URL}/releases/download/v" + "{version}/{name}"},
                "0.4.2",
                "0.28.0",
                "mac",
                "",
            ),
            (
                "opera",
                "operadriver.exe",
                "operadriver_win64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                {"url": f"{OPERA_URL}/releases/download/v." + "{version}/{name}"},
                "87.0.4280.67",
                "88.0.4324.104",
                "win",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_win64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                {"url": f"{EDGE_URL}/" + "{version}/{name}"},
                "76.0.162.0",
                "90.0.818.0",
                "win",
                "64",
            ),
        ],
    )
    def test_update_single_driver(
        self,
        driver_type,
        unarc_filename,
        arc_file_name,
        get_versions_args,
        get_file_args,
        version,
        new_version,
        os_,
        arch,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        """Update driver when only single WebDriver is present in ini file"""
        runner = CliRunner()
        content, checksum = load_driver_arc_content(tmpdir, driver_type, arc_file_name, unarc_filename)
        create_custom_ini(
            tmpdir, driver_type, filename=unarc_filename, version=version, os_=os_, arch=arch, checksum=checksum
        )
        requests_mock.get(get_versions_args["url"], **get_versions_args["kwargs"])
        requests_mock.get(get_file_args["url"].format(version=new_version, name=arc_file_name), content=content)
        create_unarc_driver(tmpdir.join(PYDRIVER_HOME), unarc_filename)
        result = runner.invoke(cli_pydriver, ["update", "-d", driver_type])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Updating {driver_type}driver")
        assert_in_log(caplog.messages, f"Updated {driver_type}driver: {version} -> {new_version}")
        assert_not_in_log(caplog.messages, "No drivers installed")
        assert get_ini_content(tmpdir) == {
            driver_type: {
                "VERSION": new_version,
                "OS": os_,
                "ARCHITECTURE": arch,
                "FILENAME": unarc_filename,
                "CHECKSUM": checksum,
            }
        }

    @pytest.mark.parametrize(
        "driver_type, unarc_filename, arc_file_name, get_versions_args, version, os_, arch",
        [
            (
                "chrome",
                "chromedriver.exe",
                "chromedriver_win32.zip",
                {"url": CHROME_URL, "kwargs": {"text": load_response("chrome")}},
                "71.0.3578.33",
                "win",
                "32",
            ),
            (
                "gecko",
                "geckodriver",
                "geckodriver-v0.28.0-linux32.tar.gz",
                {"url": GECKO_API_URL + "/releases", "kwargs": {"json": load_response("gecko")}},
                "0.28.0",
                "linux",
                "32",
            ),
            (
                "opera",
                "operadriver",
                "operadriver_linux64.zip",
                {"url": OPERA_API_URL + "/releases", "kwargs": {"json": load_response("opera")}},
                "88.0.4324.104",
                "linux",
                "64",
            ),
            (
                "edge",
                "msedgedriver.exe",
                "edgedriver_win64.zip",
                {"url": EDGE_API_URL, "kwargs": {"text": load_response("edge")}},
                "90.0.818.0",
                "win",
                "64",
            ),
        ],
    )
    def test_update_no_new_version(
        self,
        driver_type,
        unarc_filename,
        arc_file_name,
        get_versions_args,
        version,
        os_,
        arch,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        """There is single WebDriver in the ini file and there is no newer version"""
        runner = CliRunner()
        checksum = create_unarc_driver(tmpdir.join(PYDRIVER_HOME), unarc_filename)
        create_custom_ini(
            tmpdir, driver_type, filename=unarc_filename, version=version, os_=os_, arch=arch, checksum=checksum
        )
        requests_mock.get(get_versions_args["url"], **get_versions_args["kwargs"])
        result = runner.invoke(cli_pydriver, ["update", "-d", driver_type])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Updating {driver_type}driver")
        assert_in_log(
            caplog.messages, f"{driver_type}driver is already in newest version. Local: {version}, remote: {version}"
        )
        assert_not_in_log(caplog.messages, "No drivers installed")

    @pytest.mark.parametrize(
        "driver_type",
        [
            "chrome",
            "gecko",
            "opera",
            "edge",
        ],
    )
    def test_update_driver_not_in_ini(self, driver_type, tmpdir, test_dirs, env_vars, caplog, empty_ini):
        """User requested to update WebDriver that is not installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["update", "-d", driver_type])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Updating {driver_type}driver")
        assert_in_log(caplog.messages, f"Driver {driver_type}driver is not installed")
        assert_not_in_log(caplog.messages, "No drivers installed")

    @pytest.mark.parametrize(
        "driver_type",
        [
            "chrome",
            "gecko",
            "opera",
            "edge",
        ],
    )
    def test_update_driver_corrupted_ini(
        self,
        driver_type,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
    ):
        """User requested to update installed WebDriver but the ini is corrupted - missing VERSION"""
        create_custom_ini(
            tmpdir, driver_type, filename=f"{driver_type}driver", version="", os_="win", arch="32", checksum="abc1"
        )
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["update", "-d", driver_type])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, f"Updating {driver_type}driver")
        assert_in_log(caplog.messages, "Corrupted .ini file")
        assert_not_in_log(caplog.messages, "No drivers installed")

    def test_update_no_drivers_installed(
        self,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        empty_ini,
    ):
        """User requested to update all drivers but there is no drivers installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriver, ["update"])
        assert result.exit_code == 0
        assert_in_log(caplog.messages, "No drivers installed")
