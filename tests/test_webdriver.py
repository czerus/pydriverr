import logging

import pytest

from pydriverr import webdriver
from tests.helpers import PYDRIVER_HOME, PlatformUname


class TestWebdriverSystemIdentification:
    """Use WebDriver class in order to test underlying system identification"""

    @pytest.mark.parametrize(
        "user_input,expected",
        [(PlatformUname("Windows"), "win"), (PlatformUname("Darwin"), "mac"), (PlatformUname("Linux"), "linux")],
    )
    def test_system_name(self, user_input, expected, env_vars, caplog, mocker):
        """Convert output identifying system by `platform.uname` to 3 supported strings: win, mac, linux"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = user_input
        driver = webdriver.WebDriver()
        webdriver.platform.uname.assert_called()
        assert driver.system_name == expected
        assert f"Current's OS type string: {user_input.system.lower()} -> {expected}" in caplog.messages

    def test_system_name_nok(self, env_vars, caplog, mocker):
        """Display message and exit with 1 exit code when Pydriverr is run on not supported system"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname(system="nok")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        webdriver.platform.uname.assert_called()
        assert "Unknown OS type: nok" in caplog.messages

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
        """Convert output identifying system architecture by `platform.uname` to 2 supported strings: 32, 64"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = user_input
        driver = webdriver.WebDriver()
        webdriver.platform.uname.assert_called()
        assert driver.system_arch == expected
        assert f"Current's OS architecture string: {user_input.machine} -> {expected} bit" in caplog.messages

    def test_machine_nok(self, env_vars, caplog, mocker):
        """Display message and exit with 1 exit code when Pydriverr is run on not supported system architecture"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname(machine="nok")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        webdriver.platform.uname.assert_called()
        assert "Unknown architecture: nok" in caplog.messages

    def test__get_drivers_home(self, env_vars, tmpdir, caplog, mocker):
        """Test path in DRIVERS_HOME env variable is set to existing directory"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        webdriver.WebDriver()
        assert f"{webdriver.WebDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.messages

    def test__get_drivers_home_nok(self, caplog, mocker, monkeypatch):
        """Test missing path in DRIVERS_HOME env variable"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        monkeypatch.setenv(webdriver.WebDriver._ENV_NAME, "")
        with pytest.raises(SystemExit) as excinfo:
            webdriver.WebDriver()
        assert str(excinfo.value) == "1"
        assert f"Env variable '{webdriver.WebDriver._ENV_NAME}' not defined" in caplog.messages

    def test_printed_logs(self, env_vars, tmpdir, caplog, mocker):
        """Test proper messages are regarding system identification are in logs"""
        caplog.set_level(logging.DEBUG)
        webdriver.platform = mocker.Mock()
        webdriver.platform.uname.return_value = PlatformUname()
        webdriver.WebDriver()
        assert "Current's OS architecture string: AMD64 -> 64 bit" in caplog.messages
        assert "Current's OS type string: windows -> win" in caplog.messages
        assert f"{webdriver.WebDriver._ENV_NAME} set to {tmpdir.join(PYDRIVER_HOME)}" in caplog.messages
        assert "Identified OS: win" in caplog.messages
        assert "Identified architecture: 64" in caplog.messages
