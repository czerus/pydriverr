import os
import tempfile
from typing import Tuple, Union

import fire

from pydriver.logger import Logger
from pydriver.support import Support
from pydriver.webdriver import WebDriver


class PyDriver:
    """
    Download and manage webdrivers for selenium from single app
    """

    def __init__(self):
        log_path = os.path.join(tempfile.gettempdir(), "pydriver.log")
        self._logger = Logger(log_path).configure_logging()
        self._custom_driver_obj = None
        self._webdriver = None
        self._support = Support()
        self._logger.debug("{:=>10}Starting new request{:=>10}".format("", ""))

    def __set_custom_driver_obj(self, driver_type: str):
        if driver_type == "chrome":
            from pydriver.chromedriver import ChromeDriver

            self._custom_driver_obj = ChromeDriver()
        elif driver_type == "gecko":
            from pydriver.geckodriver import GeckoDriver

            self._custom_driver_obj = GeckoDriver()
        else:
            self._support.exit(f"Invalid driver type: {driver_type}")

    def show_env(self) -> None:
        """Show used directories points"""
        self._webdriver = WebDriver()
        self._logger.info(
            f"WebDrivers are installed in: {self._webdriver.drivers_home}, total size is: "
            f"{self._support.calculate_dir_size(self._webdriver.drivers_home)}"
        )
        self._logger.info(
            f"PyDriver cache is in: {self._webdriver.cache_dir}, total size is: "
            f"{self._support.calculate_dir_size(self._webdriver.cache_dir)}"
        )

    def show_installed(self) -> None:
        """List drivers installed at DRIVERS_HOME"""
        self._webdriver = WebDriver()
        if not self._webdriver.drivers_home.is_dir():
            self._support.exit(f"{self._webdriver.drivers_home} directory does not exist")
        self._webdriver.print_drivers_from_ini()

    def show_available(self, driver_type: str) -> None:
        """List drivers on remote server"""
        self.__set_custom_driver_obj(driver_type)
        self._custom_driver_obj.get_remote_drivers_list()
        self._logger.info(f"Available {driver_type} drivers:")
        self._custom_driver_obj.webdriver.print_remote_drivers()

    def clear_cache(self) -> None:
        """Delete cache directory"""
        self._webdriver = WebDriver()
        self._logger.info(f"Removing cache directory: {self._webdriver.cache_dir}")
        self._webdriver.clear_cache()

    def install(
        self,
        driver_type: str,
        version: Union[str, float, int] = "",
        os_: str = "",
        arch: str = "",
    ) -> None:
        """Download certain version of given WebDriver type"""
        self.__set_custom_driver_obj(driver_type)
        self._custom_driver_obj.get_driver(str(version), str(os_), str(arch))

    def delete(self, *driver_type: Tuple[str]) -> None:
        self._webdriver = WebDriver()
        """Remove given driver-type or all installed drivers"""
        self._webdriver.delete_drivers(driver_type)

    def update(self, *driver_type: Tuple[str]) -> None:
        """Update given WebDriver or all installed WebDrivers

        :param driver_type: Type of the WebDriver e.g. chrome, gecko"""
        if len(driver_type) == 0:
            driver_type = WebDriver().drivers_state.sections
        if driver_type:
            for driver in driver_type:
                self.__set_custom_driver_obj(driver)
                self._custom_driver_obj.update()
        else:
            self._logger.info("No drivers installed")


def main():
    fire.Fire(PyDriver)


if __name__ == "__main__":
    main()
