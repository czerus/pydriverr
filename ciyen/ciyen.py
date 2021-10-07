import click

from ciyen.ciyen_types import Drivers, OptionalString, Version
from ciyen.config import LOGGING_CONF, WebDriverType
from ciyen.custom_logger import logger
from ciyen.support import Support
from ciyen.webdriver import WebDriver

__all__ = ["cli_ciyen", "install", "delete", "update", "show_env", "show_installed", "show_available", "clear_cache"]

logger.configure(**LOGGING_CONF)
logger.debug("{:=>10}Starting new session{:=>10}".format("", ""))


class _Ciyen:
    """Provide main functionality of ciyen by initing all the required subclasses in proper way"""

    def __init__(self, driver_type: OptionalString = None):
        self.support = Support()
        self.webdriver_obj = driver_type

    @property
    def webdriver_obj(self):
        return self._webdriver_obj

    @webdriver_obj.setter
    def webdriver_obj(self, driver_type: OptionalString) -> None:
        """
        Init WebDriver like object.

        For context free commands i.e. delete, show-env, show-installed, clear-cache, init WebDriver class.
        For methods that have context (run with option `-d`) init class for given driver type e.g. OperaDriver,
        ChromeDriver, GeckoDriver.

        :param driver_type: Type of the WebDriver i.e. chrome, gecko, opera, edge
        :return: None
        """
        if not driver_type:
            self._webdriver_obj = WebDriver()
        elif driver_type == "chrome":
            from ciyen.chromedriver import ChromeDriver

            self._webdriver_obj = ChromeDriver()
        elif driver_type == "gecko":
            from ciyen.geckodriver import GeckoDriver

            self._webdriver_obj = GeckoDriver()
        elif driver_type == "opera":
            from ciyen.operadriver import OperaDriver

            self._webdriver_obj = OperaDriver()
        elif driver_type == "edge":
            from ciyen.edgedriver import EdgeDriver

            self._webdriver_obj = EdgeDriver()


@click.group()
def cli_ciyen():
    """
    Download and manage selenium WebDrivers from a single app

    \f
    click group that holds all functions under common parent name
    """
    pass


@cli_ciyen.command(short_help="Show used directories and their size")
def show_env() -> None:
    """
    Show where WebDrivers are downloaded to and cache dir with usage data

    Examples:

    \b
        Show paths to WebDrivers installation dir and cache dir. Show dirs size
        $ ciyen show-env
    """
    with logger.spinner("Show environment"):
        driver = _Ciyen()
        logger.info(
            f"WebDrivers are installed in: {driver.webdriver_obj.drivers_home}, total size is: "
            f"{driver.support.calculate_dir_size(driver.webdriver_obj.drivers_home)}"
        )
        logger.info(
            f"Ciyen cache is in: {driver.webdriver_obj.cache_dir}, total size is: "
            f"{driver.support.calculate_dir_size(driver.webdriver_obj.cache_dir)}"
        )


@cli_ciyen.command(short_help="List installed WebDrivers in a form of table")
def show_installed() -> None:
    """
    List installed WebDrivers in a form of table

    Examples:

    \b
        Show all installed WebDrivers
        $ ciyen show-installed
    """
    with logger.spinner("Show installed drivers"):
        driver = _Ciyen()
        if not driver.webdriver_obj.drivers_home.is_dir():
            driver.support.exit(f"{driver.webdriver_obj.drivers_home} directory does not exist")
        driver.webdriver_obj.print_drivers_from_ini()


@cli_ciyen.command(short_help="List of WebDrivers available to install - of given type")
@click.option(
    "-d",
    "--driver-type",
    type=click.Choice(WebDriverType.list()),
    required=True,
    help="Type of the WebDriver e.g. chrome, gecko",
)
def show_available(driver_type: str) -> None:
    """
    List of WebDrivers available to install - of given type

    Examples:

    \b
        Show list of WebDrivers available to install for given driver type.
        List contains versions and supported OS and architectures
        $ ciyen show-available -d chrome

    \f
    :param driver_type: Type of the WebDriver e.g. chrome, gecko
    """
    with logger.spinner(f"Show available drivers for: [{driver_type}]"):
        driver = _Ciyen(driver_type)
        driver.webdriver_obj.get_remote_drivers_list()
        logger.info(f"Available {driver_type} drivers:")
        driver.webdriver_obj.print_remote_drivers()


@cli_ciyen.command(short_help="Delete cache directory")
def clear_cache() -> None:
    """
    Delete cache directory

    \b
    Cache directory grows while new drivers are downloaded.

    Examples:

    \b
        Delete cache directory, it will be recreated on next ciyen run
        $ pydrive clear-cache
    """
    with logger.spinner("Clear cache"):
        driver = _Ciyen()
        logger.info(f"Removing cache directory: {driver.webdriver_obj.cache_dir}")
        driver.webdriver_obj.clear_cache()


@cli_ciyen.command(short_help="Download certain version of given WebDriver type")
@click.option(
    "-d",
    "--driver-type",
    type=click.Choice(WebDriverType.list()),
    required=True,
    help="Type of the WebDriver e.g. chrome, gecko",
)
@click.option("-v", "--version", default="", help="Version of requested WebDriver (default: newest)")
@click.option("-o", "--os", "os_", default="", help="Operating System for requested WebDriver (default: current OS)")
@click.option("-a", "--arch", default="", help="Architecture for requested WebDriver (default: current OS architecture")
def install(
    driver_type: str,
    version: Version = "",
    os_: str = "",
    arch: str = "",
) -> None:
    """
    Download certain version of given WebDriver type

    Examples:

    \b
        Install newest chrome WebDriver for OS and arch on which ciyen is run:
        $ ciyen install -d chrome
    \b
        Install given chrome Webdriver version for OS and arch on which ciyen is run:
        $ ciyen install -d chrome -v 89.0.4389.23
    \b
        Install newest gecko WebDriver for given OS but the arch is taken from current OS:
        $ ciyen install -d gecko -o linux
    \b
        Install given gecko WebDriver version for given OS and arch, no matter the current OS
        $ ciyen install -d gecko -v 0.28.0 -o linux -a 64
    \b
        Install newest gecko WebDriver for current OS and 64 bit arch
        $ ciyen install -d gecko -a 64

    \f
    :param driver_type: Type of the WebDriver e.g. chrome, gecko
    :param version: Version of requested WebDriver (default: newest)
    :param os_: Operating System for requested WebDriver (default: current OS)
    :param arch: Architecture for requested WebDriver (default: current OS architecture
    """

    with logger.spinner(f"Install driver for: [{driver_type}]"):
        driver = _Ciyen(driver_type)
        driver.webdriver_obj.install(str(version), str(os_), str(arch))


@cli_ciyen.command(short_help="Delete given WebDriver or all installed WebDrivers")
@click.option(
    "-d",
    "--driver-type",
    multiple=True,
    type=click.Choice(WebDriverType.list()),
    default="",
    help="Type of the WebDriver e.g. chrome, gecko",
)
def delete(driver_type: Drivers) -> None:
    """
    Delete given WebDriver or all installed WebDrivers

    Examples:

    \b
        Remove installed chrome WebDriver:
        $ ciyen delete -d chrome
    \b
        Remove installed chrome and gecko WebDrivers:
        $ ciyen delete -d chrome -d gecko
    \b
        Remove all installed WebDrivers:
        $ ciyen delete

    \f
    :param driver_type: Type of the WebDriver e.g. chrome, gecko
    """
    if not driver_type:
        spinner_msg = "all"
    else:
        spinner_msg = ", ".join(driver_type)

    with logger.spinner(f"Deleting driver for: [{spinner_msg}]"):
        driver = _Ciyen()
        driver.webdriver_obj.delete_drivers(driver_type)


@cli_ciyen.command(short_help="Update given WebDriver or all installed WebDrivers")
@click.option(
    "-d",
    "--driver-type",
    multiple=True,
    type=click.Choice(WebDriverType.list()),
    default="",
    help="Type of the WebDriver e.g. chrome, gecko",
)
def update(driver_type: Drivers) -> None:
    """
    Update given WebDriver or all installed WebDrivers

     Examples:

    \b
        Update chrome WebDriver:
        $ ciyen update -d chrome
    \b
        Update chrome and gecko WebDrivers:
        $ ciyen update -d chrome -d gecko
    \b
        Update all installed WebDrivers:
        $ ciyen update

    \f
    :param driver_type: Type of the WebDriver e.g. chrome, gecko
    """
    if not driver_type:
        spinner_msg = "all"
    else:
        spinner_msg = ", ".join(driver_type)

    with logger.spinner(f"Update driver for: [{spinner_msg}]"):
        if len(driver_type) == 0:
            driver_type = WebDriver().drivers_state.sections
        if driver_type:
            for installed_driver in driver_type:
                driver = _Ciyen(installed_driver)
                driver.webdriver_obj.update()
        else:
            logger.info("No drivers installed")