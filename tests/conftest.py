import logging
import platform

import pytest
from loguru import logger

from pydriverr import webdriver
from tests.helpers import CACHE_DIR, PYDRIVER_HOME, IniFile

DRIVERS_CFG = (
    IniFile()
    .add_driver(
        driver_type="chrome",
        filename="chromedriver.exe",
        version="81.0.4044.20",
        os_="win",
        arch="32",
        checksum="56db17c16d7fc9003694a2a01e37dc87",
    )
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
)


@pytest.fixture
def test_dirs(tmpdir):
    """Create directories"""
    tmpdir.mkdir(PYDRIVER_HOME)
    tmpdir.mkdir(CACHE_DIR)


@pytest.fixture
def create_ini(tmpdir):
    """Create prefilled `.drivers.ini` file"""
    DRIVERS_CFG.write(tmpdir)


@pytest.fixture
def empty_ini(tmpdir):
    """Create empty `.drivers.ini` file"""
    IniFile().write(tmpdir)


@pytest.fixture
def env_vars(monkeypatch, tmpdir):
    """Set DRIVERS_HOME environment variable for tests"""
    monkeypatch.setenv(webdriver.WebDriver._ENV_NAME, str(tmpdir.join(PYDRIVER_HOME)))
    system = platform.system().lower()
    if system == "windows":
        monkeypatch.setenv("USERPROFILE", str(tmpdir))
    elif system in ["linux", "darwin"]:
        monkeypatch.setenv("HOME", str(tmpdir))
    else:
        raise Exception(f"Unsupported system: {system}")


@pytest.fixture
def caplog(caplog):
    """Override pytest caplog fixture in order to work properly with loguru module"""

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropagateHandler(), format="{message}")
    yield caplog
    logger.remove(handler_id)
