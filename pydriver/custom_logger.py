import sys
from contextlib import contextmanager

import loguru
from yaspin import yaspin

__all__ = ["logger"]


class __MyLogger:
    """Logger class that combine luguru with yaspin for writing during spinner"""

    __GREEN = "\033[0;32m%s\033[0m"

    def __init__(self):
        self.loguru_ = loguru.logger
        self.sp = yaspin()
        self.sp.color = "green"

    def info(self, msg: str) -> None:
        """
        Hide spinner and execute loguru.info

        :param msg: Message for loguru.info
        """
        with self.sp.hidden():
            self.loguru_.info(msg)

    def debug(self, msg: str) -> None:
        """
        Hide spinner and execute loguru.debug

        :param msg: Message for loguru.debug
        """
        with self.sp.hidden():
            self.loguru_.debug(msg)

    def error(self, msg: str) -> None:
        """
        Hide spinner and execute loguru.error

        :param msg: Message for loguru.error
        """
        with self.sp.hidden():
            self.loguru_.error(msg)

    def configure(self, **kwargs: dict) -> None:
        """
        Configure loguru

        :param kwargs: Dictionary with loguru config
        """
        self.loguru_.configure(**kwargs)

    @contextmanager
    def spinner(self, msg: str) -> None:
        """
        Context manager to show spinner with given message
        :param msg: Message to be visible together with spinner
        """
        self.sp.text = msg
        self.sp.start()
        try:
            yield
            self.sp.green.ok("✔ ")
        except SystemExit as e:
            self.sp.red.fail("❌ ")
            sys.exit(e)
        finally:
            self.sp.stop()


logger = __MyLogger()
