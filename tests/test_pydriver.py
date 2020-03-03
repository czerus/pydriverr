import os
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
from configobj import ConfigObj

from pydriver import pydriver

NOT_SUPPORTED = "not_supported"
PYDRIVER_HOME = "pydriver_home"
CACHE_DIR = "pydriver_cache"
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
            "VERSION": "81.0.4044.20",
            "OS": "win",
            "ARCHITECTURE": "32",
            "FILENAME": "gecko.exe",
            "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
            "IN_INI": True,
        }
    ],
}


def create_drivers(tmpdir, file_type=None):
    for driver_type, driver_list in DRIVERS_CFG.items():
        tmpdir.join(CACHE_DIR).mkdir(driver_type)
        for driver in driver_list:
            version_dir = os.path.join(tmpdir, CACHE_DIR, driver_type, driver["VERSION"])
            if not os.path.exists(version_dir):
                os.mkdir(version_dir)
            unzip_filename = driver["FILENAME"]
            zip_filename = f"{driver['FILENAME'].replace('.exe', '')}_{driver['OS']}{driver['ARCHITECTURE']}.zip"
            content = 10 * zip_filename
            if file_type in ["both", "unzip"] and driver.get("IN_INI"):
                with open(tmpdir.join(PYDRIVER_HOME, unzip_filename), "w") as f:
                    f.write(content)
            if file_type in ["both", "zip"]:
                with ZipFile(os.path.join(version_dir, zip_filename), "w") as myzip:
                    myzip.writestr(content, unzip_filename)


@pytest.fixture
def test_dirs(tmpdir):
    tmpdir.mkdir(PYDRIVER_HOME)
    tmpdir.mkdir(CACHE_DIR)


@pytest.fixture
def create_unziped(tmpdir):
    create_drivers(tmpdir, "unzip")


@pytest.fixture
def create_zip(tmpdir):
    create_drivers(tmpdir, "zip")


@pytest.fixture
def create_both(tmpdir):
    create_drivers(tmpdir, "both")


@pytest.fixture
def create_ini(tmpdir):
    conf_obj = ConfigObj()
    conf_obj.filename = tmpdir.join(PYDRIVER_HOME, ".drivers.ini")
    for driver_type, cached_drivers in DRIVERS_CFG.items():
        for driver in cached_drivers:
            if driver.get("IN_INI"):
                conf_obj[driver_type] = driver
    conf_obj.write()


@pytest.fixture
def empty_ini(tmpdir):
    with open(os.path.join(tmpdir, PYDRIVER_HOME, ".drivers.ini"), "w") as f:
        f.write("\n\n")


@pytest.fixture
def env_vars(monkeypatch, tmpdir):
    monkeypatch.setenv(pydriver.PyDriver._ENV_NAME, str(tmpdir.join(PYDRIVER_HOME)))


@pytest.fixture
def load_chrome_xml():
    path_chrome = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "chrome.xml")
    with open(path_chrome) as f:
        content = f.read()
    return content


@pytest.fixture
def load_chrome_driver():
    path_chrome = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "chromedriver_win32.zip")
    with open(path_chrome, "rb") as f:
        content = f.read()
    return content


def copy_chrome_file(dst: Path):
    src = Path(os.path.dirname(os.path.abspath(__file__)) / Path("resources") / Path("chromedriver_win32.zip"))
    os.makedirs(dst, exist_ok=True)
    shutil.copy(src, dst)


expected_chrome = """    VERSION       OS     ARCHITECTURE
--  ------------  -----  --------------
 0  2.0           linux  32 64
 1  2.0           mac    32
 2  2.0           win    32
 3  2.1           linux  32 64
 4  2.1           mac    32
 5  71.0.3578.33  linux  64
 6  71.0.3578.33  mac    64
 7  71.0.3578.33  win    32"""


class PlatformUname:
    def __init__(self, system="Windows", machine="AMD64"):
        self.system = system
        self.machine = machine


class TestPyDriverInit:
    @pytest.mark.parametrize(
        "user_input,expected",
        [(PlatformUname("Windows"), "win"), (PlatformUname("Darwin"), "mac"), (PlatformUname("Linux"), "linux")],
    )
    def test_system_name(self, user_input, expected, env_vars, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = user_input
        pd = pydriver.PyDriver()
        pydriver.platform.uname.assert_called()
        assert pd.system_name == expected
        assert f"Current's OS type string: {user_input.system.lower()} -> {expected}" in caplog.text

    def test_system_name_nok(self, env_vars, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname(system="nok")
        with pytest.raises(SystemExit) as excinfo:
            pydriver.PyDriver()
        assert str(excinfo.value) == "1"
        pydriver.platform.uname.assert_called()
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
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = user_input
        pd = pydriver.PyDriver()
        pydriver.platform.uname.assert_called()
        assert pd.system_arch == expected
        assert f"Current's OS architecture string: {user_input.machine} -> {expected} bit" in caplog.text

    def test_machine_nok(self, env_vars, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname(machine="nok")
        with pytest.raises(SystemExit) as excinfo:
            pydriver.PyDriver()
        assert str(excinfo.value) == "1"
        pydriver.platform.uname.assert_called()
        assert "Unknown architecture: nok" in caplog.text

    def test__get_drivers_home(self, env_vars, tmpdir, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pydriver.PyDriver()
        assert f"{pydriver.PyDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.text

    def test__get_drivers_home_nok(self, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        with pytest.raises(SystemExit) as excinfo:
            pydriver.PyDriver()
        assert str(excinfo.value) == "1"
        assert f"Env variable '{pydriver.PyDriver._ENV_NAME}' not defined" in caplog.text

    def test_printed_logs(self, env_vars, tmpdir, caplog, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pydriver.PyDriver()
        assert "{:=>10}Starting new request{:=>10}".format("", "") in caplog.text
        assert "Current's OS architecture string: AMD64 -> 64 bit" in caplog.text
        assert "Current's OS type string: windows -> win" in caplog.text
        assert f"{pydriver.PyDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.text
        assert "Identified OS: win" in caplog.text
        assert "Identified architecture: 64" in caplog.text


class TestShowEnv:
    def test_show_env_empty_empty(self, env_vars, caplog, tmpdir, test_dirs, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.show_env()
        assert f"WebDrivers are installed in: {tmpdir.join(PYDRIVER_HOME)}, total size is: 0 bytes" in caplog.text
        assert f"PyDriver cache is in: {tmpdir.join(CACHE_DIR)}, total size is: 0 bytes" in caplog.text

    def test_show_env_empty_with_files(self, env_vars, caplog, tmpdir, test_dirs, create_ini, create_both, mocker):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        mocker.patch("pydriver.pydriver.humanfriendly.format_size").side_effect = ["365 bytes", "1.69 KB"]
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.show_env()
        cache_full_path = Path(tmpdir.join(CACHE_DIR))
        pydriver_home_full_path = Path(tmpdir.join(PYDRIVER_HOME))
        print("+++++++++++++++++++++++++++++++++++++=")
        print(caplog.text)
        assert f"PyDriver cache is in: {cache_full_path}, total size is: 1.69 KB" in caplog.text
        assert f"WebDrivers are installed in: {pydriver_home_full_path}, total size is: 365 bytes" in caplog.text


class TestInstalledDrivers:
    def test_installed_drivers_empty_ini(self, env_vars, tmpdir, test_dirs, empty_ini, mocker, caplog):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        with pytest.raises(SystemExit) as excinfo:
            pd.installed_drivers()
        assert "No drivers installed" in caplog.text
        assert str(excinfo.value) == "1"

    def test_installed_drivers_driver_home_does_not_exist(self, env_vars, tmpdir, test_dirs, empty_ini, mocker, caplog):
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        tmpdir.remove()
        with pytest.raises(SystemExit) as excinfo:
            pd.installed_drivers()
        assert f"{tmpdir.join(PYDRIVER_HOME)} directory does not exist" in caplog.text
        assert str(excinfo.value) == "1"

    def test_installed_drivers_installed(self, env_vars, tmpdir, test_dirs, create_both, create_ini, caplog, mocker):
        expected = """    DRIVER TYPE    VERSION       OS      ARCHITECTURE  FILENAME          CHECKSUM
--  -------------  ------------  ----  --------------  ----------------  --------------------------------
 0  chrome         81.0.4044.20  win               32  chromedriver.exe  56db17c16d7fc9003694a2a01e37dc87
 1  gecko          81.0.4044.20  win               32  gecko.exe         56db17c16d7fc9003694a2a01e37dc87"""
        pydriver.platform = mocker.Mock()
        pydriver.platform.uname.return_value = PlatformUname()
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.installed_drivers()
        assert expected in caplog.messages


class TestListDrivers:
    @pytest.mark.parametrize(
        "driver_type, expected_printout",
        [
            ("chrome", expected_chrome),
        ],
    )
    def test_list_drivers(
        self, driver_type, expected_printout, tmpdir, env_vars, caplog, requests_mock, load_chrome_xml
    ):
        pd = pydriver.PyDriver()
        requests_mock.get(pd._global_config[driver_type]["url"], text=load_chrome_xml)
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.list_drivers(driver_type)
        assert expected_chrome in caplog.messages

    def test_list_drivers_not_supported_driver(self, env_vars, caplog):
        pd = pydriver.PyDriver()
        with pytest.raises(SystemExit) as excinfo:
            pd.list_drivers(NOT_SUPPORTED)
        assert (
            f"Invalid driver type: not_supported. Supported types: {', '.join(pd._global_config.keys())}"
            in caplog.messages
        )
        assert str(excinfo.value) == "1"

    def test_list_drivers_network_error(self, env_vars, tmpdir, caplog, requests_mock):
        pd = pydriver.PyDriver()
        driver_type = list(pd._global_config.keys())[0]
        driver_url = pd._global_config[driver_type]["url"]
        requests_mock.get(driver_url, status_code=404)
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        with pytest.raises(SystemExit) as excinfo:
            pd.list_drivers(driver_type)
        assert f"Cannot download file {driver_url}" in caplog.messages
        assert str(excinfo.value) == "1"


class TestDeleteDriver:
    def test_delete_driver_no_drivers_installed(self, tmpdir, env_vars, caplog):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        with pytest.raises(SystemExit) as excinfo:
            pd.delete_driver("driver_type")
        assert "No drivers installed" in caplog.messages
        assert str(excinfo.value) == "1"

    def test_delete_driver_driver_not_installed(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.delete_driver("not_installed")
        assert "Driver: not_installed is not installed" in caplog.messages

    def test_delete_driver_single_driver(self, tmpdir, test_dirs, env_vars, caplog, create_ini, create_both):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.delete_driver("chrome")
        assert "Driver chrome removed from ini" in caplog.messages
        assert "Driver file deleted: chromedriver.exe" in caplog.messages
        assert "Driver: chrome deleted" in caplog.messages
        assert dict(pd._drivers_state) == {
            "gecko": {
                "VERSION": "81.0.4044.20",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": "gecko.exe",
                "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
                "IN_INI": "True",
            }
        }

    def test_delete_driver_many_drivers(self, tmpdir, test_dirs, env_vars, caplog, create_ini, create_both):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.delete_driver()
        assert "Driver chrome removed from ini" in caplog.messages
        assert "Driver file deleted: chromedriver.exe" in caplog.messages
        assert "Driver: chrome deleted" in caplog.messages

        assert "Driver gecko removed from ini" in caplog.messages
        assert "Driver file deleted: gecko.exe" in caplog.messages
        assert "Driver: gecko deleted" in caplog.messages
        assert dict(pd._drivers_state) == {}

    def test_delete_driver_file_does_not_exist(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        pd.delete_driver("chrome")
        assert "Driver chrome removed from ini" in caplog.messages
        assert "Driver file not found: chromedriver.exe" in caplog.messages
        assert "Driver: chrome deleted" in caplog.messages
        assert dict(pd._drivers_state) == {
            "gecko": {
                "VERSION": "81.0.4044.20",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": "gecko.exe",
                "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
                "IN_INI": "True",
            }
        }


class TestInstallDriver:
    def test_install_driver_not_supported_driver(self, env_vars, caplog):
        pd = pydriver.PyDriver()
        with pytest.raises(SystemExit) as excinfo:
            pd.install_driver(NOT_SUPPORTED, "71.0.3578.33", "win", "32")
        assert (
            f"Invalid driver type: not_supported. Supported types: {', '.join(pd._global_config.keys())}"
            in caplog.messages
        )
        assert str(excinfo.value) == "1"

    def test_install_driver_newest_version_not_in_cache(
        self, tmpdir, test_dirs, env_vars, caplog, requests_mock, load_chrome_xml, load_chrome_driver
    ):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        chrome_url = pd._global_config["chrome"]["url"]
        requests_mock.get(chrome_url, text=load_chrome_xml)
        requests_mock.get(f"{chrome_url}/71.0.3578.33/chromedriver_win32.zip", content=load_chrome_driver)
        pd.install_driver("chrome", "", "win", "32")
        assert "Requested version: , OS: win, arch: 32" in caplog.messages
        assert "Highest version of driver is: 71.0.3578.33" in caplog.messages
        assert "Requested driver not found in cache" in caplog.messages
        assert "I will download following version: 71.0.3578.33, OS: win, arch: 32" in caplog.messages
        assert "Installed chromedriver:\nVERSION: 71.0.3578.33\nOS: win\nARCHITECTURE: 32" in caplog.messages
        assert dict(pd._drivers_state) == {
            "chrome": {
                "VERSION": "71.0.3578.33",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": Path("chromedriver.exe"),
                "CHECKSUM": "64a8343fcd1ea08cf017bf5989e9ae19",
            }
        }

    def test_install_driver_invalid_os(self, tmpdir, test_dirs, env_vars, caplog, requests_mock, load_chrome_xml):
        pd = pydriver.PyDriver()
        requests_mock.get(pd._global_config["chrome"]["url"], text=load_chrome_xml)
        with pytest.raises(SystemExit) as excinfo:
            pd.install_driver("chrome", "71.0.3578.33", "Koko", "32")
        assert "There is no such OS Koko for version: 71.0.3578.33"
        assert str(excinfo.value) == "1"

    def test_install_driver_invalid_version(self, tmpdir, test_dirs, env_vars, caplog, requests_mock, load_chrome_xml):
        pd = pydriver.PyDriver()
        requests_mock.get(pd._global_config["chrome"]["url"], text=load_chrome_xml)
        with pytest.raises(SystemExit) as excinfo:
            pd.install_driver("chrome", "1.1.1", "win", "32")
        assert "There is no such version: 1.1.1"
        assert str(excinfo.value) == "1"

    def test_install_driver_invalid_arch(self, tmpdir, test_dirs, env_vars, caplog, requests_mock, load_chrome_xml):
        pd = pydriver.PyDriver()
        requests_mock.get(pd._global_config["chrome"]["url"], text=load_chrome_xml)
        with pytest.raises(SystemExit) as excinfo:
            pd.install_driver("chrome", "71.0.3578.33", "win", "i586")
        assert "There is no such arch i586 for version 71.0.3578.33 and OS: win"
        assert str(excinfo.value) == "1"

    def test_install_driver_already_installed(
        self, tmpdir, test_dirs, env_vars, caplog, create_ini, requests_mock, load_chrome_xml
    ):
        pd = pydriver.PyDriver()
        requests_mock.get(pd._global_config["chrome"]["url"], text=load_chrome_xml)
        with pytest.raises(SystemExit) as excinfo:
            pd.install_driver("chrome", "81.0.4044.20", "win", "32")
        assert "Requested driver already installed" in caplog.messages
        assert str(excinfo.value) == "0"

    def test_install_driver_replace_driver(
        self, tmpdir, test_dirs, env_vars, caplog, create_ini, requests_mock, load_chrome_xml
    ):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        chrome_url = pd._global_config["chrome"]["url"]
        requests_mock.get(chrome_url, text=load_chrome_xml)
        copy_chrome_file(pd._cache_dir / Path("chrome") / Path("2.0"))
        pd.install_driver("chrome", "2.0", "win", "32")
        assert "Requested version: 2.0, OS: win, arch: 32" in caplog.messages
        assert "Installed chromedriver:\nVERSION: 2.0\nOS: win\nARCHITECTURE: 32" in caplog.messages
        assert dict(pd._drivers_state) == {
            "chrome": {
                "VERSION": "2.0",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": Path("chromedriver.exe"),
                "CHECKSUM": "64a8343fcd1ea08cf017bf5989e9ae19",
            },
            "gecko": {
                "ARCHITECTURE": "32",
                "CHECKSUM": "56db17c16d7fc9003694a2a01e37dc87",
                "FILENAME": "gecko.exe",
                "IN_INI": "True",
                "OS": "win",
                "VERSION": "81.0.4044.20",
            },
        }

    def test_install_driver_in_cache(self, tmpdir, test_dirs, env_vars, caplog, requests_mock, load_chrome_xml):
        pd = pydriver.PyDriver()
        pd._cache_dir = Path(tmpdir.join(CACHE_DIR))
        chrome_url = pd._global_config["chrome"]["url"]
        requests_mock.get(chrome_url, text=load_chrome_xml)
        copy_chrome_file(pd._cache_dir / Path("chrome") / Path("2.0"))
        pd.install_driver("chrome", "2.0", "win", "32")
        assert "Requested version: 2.0, OS: win, arch: 32" in caplog.messages
        assert "Chromedriver in cache" in caplog.messages
        assert "Installed chromedriver:\nVERSION: 2.0\nOS: win\nARCHITECTURE: 32" in caplog.messages
        assert dict(pd._drivers_state) == {
            "chrome": {
                "VERSION": "2.0",
                "OS": "win",
                "ARCHITECTURE": "32",
                "FILENAME": Path("chromedriver.exe"),
                "CHECKSUM": "64a8343fcd1ea08cf017bf5989e9ae19",
            }
        }
