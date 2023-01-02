import subprocess

import pytest
import requests
from click.testing import CliRunner

from pydriverr import pydriverr
from pydriverr.pydriverr import cli_pydriverr
from tests.helpers import (
    CACHE_DIR,
    EXPECTED,
    NOT_SUPPORTED,
    PYDRIVERR_HOME,
    URLS,
    DriverData,
    IniFile,
    PlatformUname,
    create_driver_archive,
    create_extracted_driver,
    get_ini_content,
    load_driver_archive_content,
    load_response,
)


class TestShowEnv:
    def test_show_env_empty_cache_empty_install_dir(self, env_vars, caplog, tmpdir, test_dirs, mocker):
        """Size of cache and install dir is 0 bytes when there is nothing installed and nothing in cache"""
        runner = CliRunner()
        pydriverr.platform = mocker.Mock()
        pydriverr.platform.uname.return_value = PlatformUname("Windows", "AMD64")
        result = runner.invoke(cli_pydriverr, ["show-env"])
        assert result.exit_code == 0
        assert f"WebDrivers are installed in: {tmpdir.join(PYDRIVERR_HOME)}, total size is: 0 bytes" in caplog.messages
        assert f"PyDriverr cache is in: {tmpdir.join(CACHE_DIR)}, total size is: 0 bytes" in caplog.messages

    def test_show_env_empty_with_files(self, env_vars, caplog, tmpdir, test_dirs, create_ini, mocker):
        """
        Size of cache and install dir is properly displayed (numbers are in humanfriendly units) when
        some drivers are installed and there is something in cache
        """
        runner = CliRunner()
        pydriverr.platform = mocker.Mock()
        pydriverr.platform.uname.return_value = PlatformUname("Windows", "AMD64")
        mocker.patch("pydriverr.support.humanfriendly.format_size").side_effect = ["365 bytes", "1.69 KB"]
        result = runner.invoke(cli_pydriverr, ["show-env"])
        assert result.exit_code == 0
        assert f"PyDriverr cache is in: {tmpdir.join(CACHE_DIR)}, total size is: 1.69 KB" in caplog.messages
        assert (
            f"WebDrivers are installed in: {tmpdir.join(PYDRIVERR_HOME)}, total size is: 365 bytes" in caplog.messages
        )


class TestShowInstalled:
    def test_show_installed_empty_ini(self, env_vars, tmpdir, test_dirs, empty_ini, mocker, caplog):
        """Display message when ini file is empty - no drivers installed"""
        runner = CliRunner()
        pydriverr.platform = mocker.Mock()
        pydriverr.platform.uname.return_value = PlatformUname("Windows", "AMD64")
        result = runner.invoke(cli_pydriverr, ["show-installed"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert "No drivers installed" in caplog.messages

    def test_show_installed_driver_home_does_not_exist(self, env_vars, tmpdir, mocker, caplog):
        """Display message when directory configured in PYDRIVE_HOME env variable does not exist"""
        runner = CliRunner()
        pydriverr.platform = mocker.Mock()
        pydriverr.platform.uname.return_value = PlatformUname("Windows", "AMD64")
        mocker.patch("pydriverr.support.Path.mkdir")
        result = runner.invoke(cli_pydriverr, ["show-installed"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert f"{tmpdir.join(PYDRIVERR_HOME)} directory does not exist" in caplog.messages

    def test_show_installed_installed(self, env_vars, tmpdir, test_dirs, create_ini, caplog, mocker):
        """Display table with all installed drivers"""
        expected = """    DRIVER TYPE    VERSION        OS      ARCHITECTURE  FILENAME          CHECKSUM
--  -------------  -------------  ----  --------------  ----------------  --------------------------------
 0  chrome         81.0.4044.20   win               32  chromedriver.exe  56db17c16d7fc9003694a2a01e37dc87
 1  gecko          0.28.0         win               32  geckodriver.exe   56db17c16d7fc9003694a2a01e37dc87
 2  opera          88.0.4324.104  win               32  operadriver.exe   c6847807558142bec4e1bcc70ffa2387
 3  edge           90.0.818.0     win               32  msedgedriver.exe  46920536a8723dc0a68dedc3bb0f0fba"""
        runner = CliRunner()
        pydriverr.platform = mocker.Mock()
        pydriverr.platform.uname.return_value = PlatformUname("Windows", "AMD64")
        result = runner.invoke(cli_pydriverr, ["show-installed"])
        assert result.exit_code == 0
        assert expected in caplog.messages


class TestShowAvailable:
    @pytest.mark.parametrize(
        "driver_data,request_data",
        [
            (
                DriverData(type="chrome"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (DriverData(type="edge"), {"url": URLS["EDGE_API"], "kwargs": load_response("edge")}),
        ],
    )
    def test_show_available(self, driver_data, request_data, tmpdir, env_vars, caplog, requests_mock):
        """For every WebDriver type display table with all available versions of the driver"""
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(cli_pydriverr, ["show-available", "-d", driver_data.type])
        assert result.exit_code == 0
        assert EXPECTED[driver_data.type.upper()] in caplog.messages

    def test_show_available_not_supported_driver(self, env_vars, caplog):
        """Display message when WebDriver is not supported"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["show-available", "-d", NOT_SUPPORTED])
        assert result.exit_code == 2
        assert result.exc_info[0] == SystemExit

    def test_show_available_network_error(self, env_vars, tmpdir, caplog, requests_mock):
        """Display message when there is a network unavailability"""
        runner = CliRunner()
        requests_mock.get(URLS["CHROME"], exc=requests.exceptions.ConnectTimeout)
        result = runner.invoke(cli_pydriverr, ["show-available", "-d", "chrome"])
        assert result.exc_info[0] == SystemExit
        assert result.exit_code == 1
        assert "Connection error" in caplog.messages

    def test_show_available_page_not_available(self, env_vars, tmpdir, caplog, requests_mock):
        """Display message when the page with list of available drivers does not exist"""
        runner = CliRunner()
        requests_mock.get(URLS["CHROME"], status_code=404)
        result = runner.invoke(cli_pydriverr, ["show-available", "-d", "chrome"])
        assert result.exc_info[0] == SystemExit
        assert result.exit_code == 1
        assert f"Cannot download file {URLS['CHROME']}" in caplog.messages


class TestDelete:
    def test_delete_no_drivers_installed(self, tmpdir, env_vars, caplog):
        """Display message when there are no drivers installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["delete", "-d", "chrome"])
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert "No drivers installed" in caplog.messages

    def test_delete_driver_not_installed(self, tmpdir, test_dirs, env_vars, caplog, empty_ini):
        """Display message when trying to delete driver that is not installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["delete", "-d", "chrome"])
        assert result.exit_code == 0
        assert "Driver: chrome is not installed" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data",
        [
            (DriverData(type="chrome", filename="chromedriver.exe")),
            (DriverData(type="gecko", filename="geckodriver.exe")),
            (DriverData(type="opera", filename="operadriver.exe")),
            (DriverData(type="edge", filename="msedgedriver.exe")),
        ],
    )
    def test_delete_single_driver(self, driver_data, tmpdir, test_dirs, env_vars, caplog, create_ini):
        """When deleting single installed driver display proper message, remove driver's file and update ini"""
        runner = CliRunner()
        create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_data.filename)
        result = runner.invoke(cli_pydriverr, ["delete"])
        assert result.exit_code == 0
        assert f"Driver {driver_data.type} removed from ini" in caplog.messages
        assert f"Driver file deleted: {driver_data.filename}" in caplog.messages
        assert f"Driver: {driver_data.type} deleted" in caplog.messages
        assert get_ini_content(tmpdir) == {}

    def test_delete_many_drivers(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        """When deleting all installed drivers display proper message, remove driver's files and update ini"""
        runner = CliRunner()
        all_drivers = {"chrome": "chromedriver.exe", "gecko": "geckodriver.exe", "opera": "operadriver.exe"}
        for driver_type, driver_file_name in all_drivers.items():
            create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_file_name)
        result = runner.invoke(cli_pydriverr, ["delete"])
        assert result.exit_code == 0
        for driver_type, driver_file_name in all_drivers.items():
            assert f"Driver {driver_type} removed from ini" in caplog.messages
            assert f"Driver file deleted: {driver_file_name}" in caplog.messages
            assert f"Driver: {driver_type} deleted" in caplog.messages
        assert get_ini_content(tmpdir) == {}

    def test_delete_file_does_not_exist(self, tmpdir, test_dirs, env_vars, caplog, create_ini):
        """
        Do not fail but continue and show proper message when driver's file does not exist. Content of the ini
        should be updated. May happen when one deletes file manually
        """
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["delete", "-d", "chrome"])
        assert result.exit_code == 0
        assert "Driver chrome removed from ini" in caplog.messages
        assert "Driver file not found: chromedriver.exe" in caplog.messages
        assert "Driver: chrome deleted" in caplog.messages
        assert (
            get_ini_content(tmpdir)
            == IniFile()
            .add_driver(
                driver_type="gecko",
                filename="geckodriver.exe",
                version="0.28.0",
                os_="win",
                arch="32",
                checksum="56db17c16d7fc9003694a2a01e37dc87",
            )
            .add_driver(
                driver_type="opera",
                filename="operadriver.exe",
                version="88.0.4324.104",
                os_="win",
                arch="32",
                checksum="c6847807558142bec4e1bcc70ffa2387",
            )
            .add_driver(
                driver_type="edge",
                filename="msedgedriver.exe",
                version="90.0.818.0",
                os_="win",
                arch="32",
                checksum="46920536a8723dc0a68dedc3bb0f0fba",
            )
            .to_dict()
        )


class TestInstall:
    def test_install_not_supported_driver(self, env_vars, caplog):
        """Pydriverr exits with 2 exit code when requested WebDriver type is not supported"""
        runner = CliRunner()
        result = runner.invoke(
            cli_pydriverr, ["install", "-d", NOT_SUPPORTED, "-v", "71.0.3578.33", "-o", "win", "-a", "32"]
        )
        assert result.exit_code == 2
        assert result.exc_info[0] == SystemExit

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(type="chrome", version="Google Chrome 81.0.4044.20"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko", version="Mozilla Firefox 0.28.0"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera", version="88.0.4324.104"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(type="edge", version="90.0.818.0"),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_match_version_already_installed_exact_version(
        self, driver_data, request_data, test_dirs, env_vars, caplog, create_ini, requests_mock, mocker
    ):
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        mocker.patch("pydriverr.webdriver.subprocess.run").side_effect = [
            subprocess.CompletedProcess("args", 0, bytes(driver_data.version, "UTF-8"), "")
        ]
        mocker.patch("pydriverr.webdriver.platform.uname").return_value = PlatformUname("Windows", "32")
        result = runner.invoke(cli_pydriverr, ["install", "-d", driver_data.type, "-m"])
        assert result.exit_code == 0
        assert "Required version of driver already installed" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    version="71.0.3578.33",
                    os_="win",
                    arch="64",
                    filename="chromedriver.exe",
                    arc_filename="chromedriver_win64.zip",
                ),
                [
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    version="0.28.0",
                    os_="win",
                    arch="64",
                    filename="geckodriver.exe",
                    arc_filename="geckodriver-v0.28.0-win64.zip",
                ),
                [
                    {"url": URLS["GECKO"]},
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    version="88.0.4324.104",
                    os_="win",
                    arch="64",
                    filename="operadriver",
                    arc_filename="operadriver_win64.zip",
                ),
                [
                    {"url": URLS["OPERA"]},
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    version="90.0.818.0",
                    os_="win",
                    arch="64",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                [
                    {"url": URLS["EDGE"]},
                    {"url": f"{URLS['EDGE_API']}", "kwargs": load_response("edge")},
                ],
            ),
        ],
    )
    def test_install_match_version(
        self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, requests_mock, mocker
    ):
        requests_mock.get(request_data[1]["url"], **request_data[1]["kwargs"])
        mocker.patch("pydriverr.webdriver.subprocess.run").side_effect = [
            subprocess.CompletedProcess("args", 0, bytes(driver_data.version, "UTF-8"), "")
        ]
        mocker.patch("pydriverr.webdriver.platform.uname").return_value = PlatformUname("Windows", "AMD64")

        content, checksum = load_driver_archive_content(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename
        )
        requests_mock.get(
            request_data[0]["url"].format(version=driver_data.version, name=driver_data.arc_filename), content=content
        )
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["install", "-d", driver_data.type, "-m"])
        assert result.exit_code == 0
        assert f"Found webdriver nearest version: {driver_data.version} for OS: {driver_data.os_}" in caplog.messages
        assert (
            f"I will download following version: {driver_data.version}, OS: {driver_data.os_}, "
            f"arch: {driver_data.arch}" in caplog.messages
        )
        assert (
            f"Installed {driver_data.type}driver:\nVERSION: {driver_data.version}\nOS: {driver_data.os_}"
            f"\nARCHITECTURE: {driver_data.arch}" in caplog.messages
        )

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    os_="win",
                    arch="64",
                    version="71.0.3578.33",
                    filename="chromedriver.exe",
                    arc_filename="chromedriver_win64.zip",
                ),
                [
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    os_="win",
                    arch="64",
                    version="0.16.1",
                    filename="geckodriver.exe",
                    arc_filename="geckodriver-v0.16.1-win64.zip",
                ),
                [
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                    {"url": URLS["GECKO"]},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    os_="win",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver.exe",
                    arc_filename="operadriver_win64.zip",
                ),
                [
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                    {"url": URLS["OPERA"]},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="64",
                    version="76.0.165.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
            ),
        ],
    )
    def test_install_match_version_already_installed_not_exact(
        self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, create_ini, requests_mock, mocker
    ):
        """ """
        runner = CliRunner()
        content, checksum = load_driver_archive_content(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename
        )
        create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_data.filename)
        requests_mock.get(request_data[0]["url"], **request_data[0]["kwargs"])
        requests_mock.get(
            request_data[1]["url"].format(version=driver_data.version, name=driver_data.arc_filename),
            content=content,
        )
        mocker.patch("pydriverr.webdriver.subprocess.run").side_effect = [
            subprocess.CompletedProcess("args", 0, bytes(driver_data.version, "UTF-8"), "")
        ]
        mocker.patch("pydriverr.webdriver.platform.uname").return_value = PlatformUname("Windows", "AMD64")

        result = runner.invoke(cli_pydriverr, ["install", "-d", driver_data.type, "-m"])
        assert result.exit_code == 0
        assert (
            f"Requested version: {driver_data.version}, OS: {driver_data.os_}, arch: {driver_data.arch}"
            in caplog.messages
        )
        assert f"Driver file deleted: {driver_data.filename}" in caplog.messages
        assert (
            f"Installed {driver_data.type}driver:\nVERSION: {driver_data.version}\nOS: {driver_data.os_}"
            f"\nARCHITECTURE: {driver_data.arch}" in caplog.messages
        )
        assert get_ini_content(tmpdir).get(driver_data.type, {}) == IniFile().add_driver(
            driver_type=driver_data.type,
            filename=driver_data.filename,
            version=driver_data.version,
            os_=driver_data.os_,
            arch=driver_data.arch,
            checksum=checksum,
        ).to_dict().get(driver_data.type, {})

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    version="71.0.3578.33",
                    os_="win",
                    arch="32",
                    filename="chromedriver.exe",
                    arc_filename="chromedriver_win32.zip",
                ),
                [
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    version="0.28.0",
                    os_="win",
                    arch="32",
                    filename="geckodriver.exe",
                    arc_filename="geckodriver-v0.28.0-win32.zip",
                ),
                [
                    {"url": URLS["GECKO"]},
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    version="0.28.0",
                    os_="linux",
                    arch="64",
                    filename="geckodriver",
                    arc_filename="geckodriver-v0.28.0-linux64.tar.gz",
                ),
                [
                    {"url": URLS["GECKO"]},
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    version="0.28.0",
                    os_="mac",
                    filename="geckodriver",
                    arc_filename="geckodriver-v0.28.0-macos.tar.gz",
                ),
                [
                    {"url": URLS["GECKO"]},
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    version="88.0.4324.104",
                    os_="win",
                    arch="32",
                    filename="operadriver.exe",
                    arc_filename="operadriver_win32.zip",
                ),
                [
                    {"url": URLS["OPERA"]},
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    version="88.0.4324.104",
                    os_="linux",
                    arch="64",
                    filename="operadriver",
                    arc_filename="operadriver_linux64.zip",
                ),
                [
                    {"url": URLS["OPERA"]},
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    version="88.0.4324.104",
                    os_="mac",
                    arch="64",
                    filename="operadriver",
                    arc_filename="operadriver_mac64.zip",
                ),
                [
                    {"url": URLS["OPERA"]},
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    version="90.0.818.0",
                    os_="win",
                    arch="64",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                [
                    {"url": URLS["EDGE"]},
                    {"url": f"{URLS['EDGE_API']}", "kwargs": load_response("edge")},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    version="90.0.818.0",
                    os_="arm",
                    arch="64",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_arm64.zip",
                ),
                [
                    {"url": URLS["EDGE"]},
                    {"url": f"{URLS['EDGE_API']}", "kwargs": load_response("edge")},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    version="90.0.818.0",
                    os_="mac",
                    arch="64",
                    filename="msedgedriver",
                    arc_filename="edgedriver_mac64.zip",
                ),
                [
                    {"url": URLS["EDGE"]},
                    {"url": f"{URLS['EDGE_API']}", "kwargs": load_response("edge")},
                ],
            ),
        ],
    )
    def test_install_newest_version_not_in_cache(
        self,
        driver_data,
        request_data,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        """
        Display message and update ini file when installation of the newest available WebDriver is requested.
        No extra options given except driver type. Driver file is not available in cache.
        """
        requests_mock.get(request_data[1]["url"], **request_data[1]["kwargs"])
        content, checksum = load_driver_archive_content(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename
        )
        requests_mock.get(
            request_data[0]["url"].format(version=driver_data.version, name=driver_data.arc_filename), content=content
        )
        runner = CliRunner()
        result = runner.invoke(
            cli_pydriverr,
            ["install", "-d", driver_data.type, "-o", driver_data.os_, "-a", driver_data.arch],
        )
        assert result.exit_code == 0
        assert f"Requested version: , OS: {driver_data.os_}, arch: {driver_data.arch}" in caplog.messages
        assert f"Highest version of driver is: {driver_data.version}" in caplog.messages
        assert "Requested driver not found in cache" in caplog.messages
        assert (
            f"I will download following version: {driver_data.version}, OS: {driver_data.os_}, "
            f"arch: {driver_data.arch}" in caplog.messages
        )
        assert (
            f"Installed {driver_data.type}driver:\nVERSION: {driver_data.version}\nOS: {driver_data.os_}"
            f"\nARCHITECTURE: {driver_data.arch}" in caplog.messages
        )
        assert (
            get_ini_content(tmpdir)
            == IniFile()
            .add_driver(
                driver_type=driver_data.type,
                filename=driver_data.filename,
                version=driver_data.version,
                os_=driver_data.os_,
                arch=driver_data.arch,
                checksum=checksum,
            )
            .to_dict()
        )

    @pytest.mark.parametrize(
        "driver_data,request_data",
        [
            (
                DriverData(type="chrome", version="71.0.3578.33"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko", version="0.28.0"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera", version="88.0.4324.104"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(type="edge", version="90.0.818.0"),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_invalid_os(self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, requests_mock):
        """
        Pydriverr exits with 1 exit code and display message when operating system requested for given WebDriver type
        is not supported
        """
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(
            cli_pydriverr,
            ["install", "-d", driver_data.type, "-v", driver_data.version, "-o", NOT_SUPPORTED, "-a", "32"],
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert f"There is no such OS {NOT_SUPPORTED} for version: {driver_data.version}" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(type="chrome", version="1.1.1.1"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko", version="1.1.1.1"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera", version="1.1.1.1"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(type="edge", version="1.1.1.1"),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_invalid_version(
        self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, requests_mock
    ):
        """Pydriverr exits with 1 exit code and display message when version of requested WebDriver doesn't exist"""
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(
            cli_pydriverr, ["install", "-d", driver_data.type, "-v", driver_data.version, "-o", "win", "-a", "32"]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert f"There is no such version: {driver_data.version} of {driver_data.type}driver" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(type="chrome", version="71.0.3578.33"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko", version="0.28.0"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera", version="88.0.4324.104"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(type="edge", version="90.0.818.0"),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_invalid_arch(self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, requests_mock):
        """
        Pydriverr exits with 1 exit code and display message when operating system requested for given WebDriver type
        is not supported
        """
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(
            cli_pydriverr,
            ["install", "-d", driver_data.type, "-v", driver_data.version, "-o", "win", "-a", NOT_SUPPORTED],
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == SystemExit
        assert f"There is no such arch {NOT_SUPPORTED} for version {driver_data.version} and OS: win" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(type="chrome", version="81.0.4044.20"),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(type="gecko", version="0.28.0"),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(type="opera", version="88.0.4324.104"),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(type="edge", version="90.0.818.0"),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_already_installed(
        self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, create_ini, requests_mock
    ):
        """Display message when requested driver with given version, os and arch is already installed"""
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(
            cli_pydriverr, ["install", "-d", driver_data.type, "-v", driver_data.version, "-o", "win", "-a", "32"]
        )
        assert result.exit_code == 0
        assert "Requested driver already installed" in caplog.messages

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    os_="linux",
                    arch="64",
                    version="71.0.3578.33",
                    filename="chromedriver",
                    arc_filename="chromedriver_linux64.zip",
                ),
                [
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                ],
            ),
            (
                DriverData(
                    type="chrome",
                    os_="mac",
                    arch="64",
                    version="71.0.3578.33",
                    filename="chromedriver",
                    arc_filename="chromedriver_mac64.zip",
                ),
                [
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    os_="win",
                    arch="64",
                    version="0.16.1",
                    filename="geckodriver.exe",
                    arc_filename="geckodriver-v0.16.1-win64.zip",
                ),
                [
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                    {"url": URLS["GECKO"]},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    os_="linux",
                    arch="64",
                    version="0.16.1",
                    filename="geckodriver",
                    arc_filename="geckodriver-v0.16.1-linux64.tar.gz",
                ),
                [
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                    {"url": URLS["GECKO"]},
                ],
            ),
            (
                DriverData(
                    type="gecko",
                    os_="mac",
                    arch="",
                    version="0.4.2",
                    filename="wires-0.4.2-osx",
                    arc_filename="wires-0.4.2-osx.gz",
                ),
                [
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                    {"url": URLS["GECKO"]},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    os_="win",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver.exe",
                    arc_filename="operadriver_win64.zip",
                ),
                [
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                    {"url": URLS["OPERA"]},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    os_="linux",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver",
                    arc_filename="operadriver_linux64.zip",
                ),
                [
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                    {"url": URLS["OPERA"]},
                ],
            ),
            (
                DriverData(
                    type="opera",
                    os_="mac",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver",
                    arc_filename="operadriver_mac64.zip",
                ),
                [
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                    {"url": URLS["OPERA"]},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="64",
                    version="90.0.817.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    os_="mac",
                    arch="64",
                    version="90.0.817.0",
                    filename="msedgedriver",
                    arc_filename="edgedriver_mac64.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    os_="arm",
                    arch="64",
                    version="90.0.817.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_arm64.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="86",
                    version="76.0.165.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win86.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
            ),
        ],
    )
    def test_install_replace_driver(
        self,
        driver_data,
        request_data,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        create_ini,
        requests_mock,
    ):
        """
        Display message, change driver's file and update ini when different version, os or/and arch of already installed
        WebDriver is requested
        """
        runner = CliRunner()
        content, checksum = load_driver_archive_content(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename
        )
        create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_data.filename)
        requests_mock.get(request_data[0]["url"], **request_data[0]["kwargs"])
        requests_mock.get(
            request_data[1]["url"].format(version=driver_data.version, name=driver_data.arc_filename),
            content=content,
        )
        result = runner.invoke(
            cli_pydriverr,
            [
                "install",
                "-d",
                driver_data.type,
                "-v",
                driver_data.version,
                "-o",
                driver_data.os_,
                "-a",
                driver_data.arch,
            ],
        )
        assert result.exit_code == 0
        assert (
            f"Requested version: {driver_data.version}, OS: {driver_data.os_}, arch: {driver_data.arch}"
            in caplog.messages
        )
        assert (
            f"Installed {driver_data.type}driver:\nVERSION: {driver_data.version}\nOS: {driver_data.os_}"
            f"\nARCHITECTURE: {driver_data.arch}" in caplog.messages
        )
        assert get_ini_content(tmpdir).get(driver_data.type, {}) == IniFile().add_driver(
            driver_type=driver_data.type,
            filename=driver_data.filename,
            version=driver_data.version,
            os_=driver_data.os_,
            arch=driver_data.arch,
            checksum=checksum,
        ).to_dict().get(driver_data.type, {})

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    os_="linux",
                    arch="64",
                    version="71.0.3578.33",
                    filename="chromedriver",
                    arc_filename="chromedriver_linux64.zip",
                ),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(
                    type="chrome",
                    os_="mac",
                    arch="64",
                    version="71.0.3578.33",
                    filename="chromedriver",
                    arc_filename="chromedriver_mac64.zip",
                ),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(
                    type="gecko",
                    os_="win",
                    arch="64",
                    version="0.28.0",
                    filename="geckodriver.exe",
                    arc_filename="geckodriver-v0.28.0-win64.zip",
                ),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(
                    type="gecko",
                    os_="mac",
                    arch="",
                    version="0.4.2",
                    filename="wires-0.4.2-osx",
                    arc_filename="wires-0.4.2-osx.gz",
                ),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(
                    type="opera",
                    os_="win",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver.exe",
                    arc_filename="operadriver_win64.zip",
                ),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(
                    type="opera",
                    os_="linux",
                    arch="64",
                    version="0.1.0",
                    filename="operadriver",
                    arc_filename="operadriver_linux64.zip",
                ),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(
                    type="opera",
                    os_="mac",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver",
                    arc_filename="operadriver_mac64.zip",
                ),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="64",
                    version="90.0.818.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
            (
                DriverData(
                    type="edge",
                    os_="mac",
                    arch="64",
                    version="90.0.818.0",
                    filename="msedgedriver",
                    arc_filename="edgedriver_mac64.zip",
                ),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
            (
                DriverData(
                    type="edge",
                    os_="arm",
                    arch="64",
                    version="90.0.818.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_arm64.zip",
                ),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_install_from_cache(
        self, driver_data, request_data, tmpdir, test_dirs, env_vars, caplog, requests_mock, mocker
    ):
        """
        Display message and update ini file when installation of the newest available WebDriver is requested.
        No extra options given except driver type. Driver file is available in cache.

        """
        runner = CliRunner()
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        mocker.patch("pydriverr.webdriver.platform.uname").return_value = PlatformUname("linux", "x86_64")

        checksum = create_driver_archive(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename, version=driver_data.version
        )

        result = runner.invoke(
            cli_pydriverr,
            [
                "install",
                "-d",
                driver_data.type,
                "-v",
                driver_data.version,
                "-o",
                driver_data.os_,
                "-a",
                driver_data.arch,
            ],
        )
        assert result.exit_code == 0
        assert (
            f"Requested version: {driver_data.version}, OS: {driver_data.os_}, arch: {driver_data.arch}"
            in caplog.messages
        )
        assert f"{driver_data.type}driver in cache" in caplog.messages
        assert (
            f"Installed {driver_data.type}driver:\nVERSION: {driver_data.version}\nOS: {driver_data.os_}"
            f"\nARCHITECTURE: {driver_data.arch}" in caplog.messages
        )
        assert (
            get_ini_content(tmpdir)
            == IniFile()
            .add_driver(
                driver_type=driver_data.type,
                filename=driver_data.filename,
                version=driver_data.version,
                os_=driver_data.os_,
                arch=driver_data.arch,
                checksum=checksum,
            )
            .to_dict()
        )


class TestClearCache:
    def test_clear_cache(self, env_vars, caplog, test_dirs, tmpdir):
        """Display message after removing whole cache directory"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["clear-cache"])
        assert result.exit_code == 0
        assert f"Removing cache directory: {tmpdir.join(CACHE_DIR)}" in caplog.messages


class TestUpdate:
    @pytest.mark.parametrize(
        "driver_data, request_data, new_version",
        [
            (
                DriverData(
                    type="chrome",
                    os_="win",
                    arch="32",
                    version="2.0",
                    filename="chromedriver.exe",
                    arc_filename="chromedriver_win32.zip",
                ),
                [
                    {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
                    {"url": URLS["CHROME"] + "/{version}/{name}"},
                ],
                "71.0.3578.33",
            ),
            (
                DriverData(
                    type="gecko",
                    os_="mac",
                    arch="",
                    version="0.4.2",
                    filename="geckodriver",
                    arc_filename="geckodriver-v0.28.0-macos.tar.gz",
                ),
                [
                    {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
                    {"url": URLS["GECKO"]},
                ],
                "0.28.0",
            ),
            (
                DriverData(
                    type="opera",
                    os_="win",
                    arch="64",
                    version="87.0.4280.67",
                    filename="operadriver.exe",
                    arc_filename="operadriver_win64.zip",
                ),
                [
                    {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
                    {"url": URLS["OPERA"]},
                ],
                "88.0.4324.104",
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="64",
                    version="76.0.162.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                [
                    {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
                    {"url": URLS["EDGE"]},
                ],
                "90.0.818.0",
            ),
        ],
    )
    def test_update_single_driver(
        self,
        driver_data,
        request_data,
        new_version,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        """Update driver when only single WebDriver is present in ini file"""
        runner = CliRunner()
        content, checksum = load_driver_archive_content(
            tmpdir, driver_data.type, driver_data.arc_filename, driver_data.filename
        )
        IniFile().add_driver(
            driver_data.type,
            filename=driver_data.filename,
            version=driver_data.version,
            os_=driver_data.os_,
            arch=driver_data.arch,
            checksum=checksum,
        ).write(tmpdir)
        requests_mock.get(request_data[0]["url"], **request_data[0]["kwargs"])
        requests_mock.get(
            request_data[1]["url"].format(version=new_version, name=driver_data.arc_filename),
            content=content,
        )
        create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_data.filename)
        result = runner.invoke(cli_pydriverr, ["update", "-d", driver_data.type])
        assert result.exit_code == 0
        assert f"Updating {driver_data.type}driver" in caplog.messages
        assert f"Updated {driver_data.type}driver: {driver_data.version} -> {new_version}" in caplog.messages
        assert "No drivers installed" not in caplog.messages
        assert (
            get_ini_content(tmpdir)
            == IniFile()
            .add_driver(
                driver_type=driver_data.type,
                filename=driver_data.filename,
                version=new_version,
                os_=driver_data.os_,
                arch=driver_data.arch,
                checksum=checksum,
            )
            .to_dict()
        )

    @pytest.mark.parametrize(
        "driver_data, request_data",
        [
            (
                DriverData(
                    type="chrome",
                    os_="win",
                    arch="32",
                    version="71.0.3578.33",
                    filename="chromedriver.exe",
                    arc_filename="chromedriver_win32.zip",
                ),
                {"url": URLS["CHROME"], "kwargs": load_response("chrome")},
            ),
            (
                DriverData(
                    type="gecko",
                    os_="linux",
                    arch="32",
                    version="0.28.0",
                    filename="geckodriver",
                    arc_filename="geckodriver-v0.28.0-linux32.tar.gz",
                ),
                {"url": URLS["GECKO_API"], "kwargs": load_response("gecko")},
            ),
            (
                DriverData(
                    type="opera",
                    os_="linux",
                    arch="64",
                    version="88.0.4324.104",
                    filename="operadriver",
                    arc_filename="operadriver_linux64.zip",
                ),
                {"url": URLS["OPERA_API"], "kwargs": load_response("opera")},
            ),
            (
                DriverData(
                    type="edge",
                    os_="win",
                    arch="64",
                    version="90.0.818.0",
                    filename="msedgedriver.exe",
                    arc_filename="edgedriver_win64.zip",
                ),
                {"url": URLS["EDGE_API"], "kwargs": load_response("edge")},
            ),
        ],
    )
    def test_update_no_new_version(
        self,
        driver_data,
        request_data,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        requests_mock,
    ):
        """Update driver when there is single WebDriver in the ini file and there is no newer version"""
        runner = CliRunner()
        checksum = create_extracted_driver(tmpdir.join(PYDRIVERR_HOME), driver_data.filename)
        IniFile().add_driver(
            driver_type=driver_data.type,
            filename=driver_data.filename,
            version=driver_data.version,
            os_=driver_data.os_,
            arch=driver_data.arch,
            checksum=checksum,
        ).write(tmpdir)
        requests_mock.get(request_data["url"], **request_data["kwargs"])
        result = runner.invoke(cli_pydriverr, ["update", "-d", driver_data.type])
        assert result.exit_code == 0
        assert f"Updating {driver_data.type}driver" in caplog.messages
        assert (
            f"{driver_data.type}driver is already in newest version. Local: {driver_data.version}, "
            f"remote: {driver_data.version}" in caplog.messages
        )
        assert "No drivers installed" not in caplog.messages

    @pytest.mark.parametrize(
        "driver_data",
        [
            DriverData(type="chrome"),
            DriverData(type="gecko"),
            DriverData(type="opera"),
            DriverData(type="edge"),
        ],
    )
    def test_update_driver_not_in_ini(self, driver_data, tmpdir, test_dirs, env_vars, caplog, empty_ini):
        """Update WebDriver that is not installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["update", "-d", driver_data.type])
        assert result.exit_code == 0
        assert f"Updating {driver_data.type}driver" in caplog.messages
        assert f"Driver {driver_data.type}driver is not installed" in caplog.messages
        assert "No drivers installed" not in caplog.messages

    @pytest.mark.parametrize(
        "driver_data",
        [
            DriverData(type="chrome"),
            DriverData(type="gecko"),
            DriverData(type="opera"),
            DriverData(type="edge"),
        ],
    )
    def test_update_driver_corrupted_ini(
        self,
        driver_data,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
    ):
        """Update installed WebDriver but the ini is corrupted - missing VERSION"""
        IniFile().add_driver(
            driver_type=driver_data.type,
            filename=f"{driver_data.type}driver",
            version="",
            os_="win",
            arch="32",
            checksum="abc1",
        ).write(tmpdir)
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["update", "-d", driver_data.type])
        assert result.exit_code == 0
        assert f"Updating {driver_data.type}driver" in caplog.messages
        assert "Corrupted .ini file" in caplog.messages
        assert "No drivers installed" not in caplog.messages

    def test_update_no_drivers_installed(
        self,
        tmpdir,
        test_dirs,
        env_vars,
        caplog,
        empty_ini,
    ):
        """Update all drivers but there are no drivers installed"""
        runner = CliRunner()
        result = runner.invoke(cli_pydriverr, ["update"])
        assert result.exit_code == 0
        assert "No drivers installed" in caplog.messages
