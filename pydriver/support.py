import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import List

import humanfriendly
from loguru import logger
from configobj import ConfigObj
from config import CACHE_DIR, DRIVERS_CFG
from pydriver.pydriver_types import Messages


class Support:
    """Helper methods"""

    @staticmethod
    def calculate_checksum(filepath: Path) -> str:
        """
        Calculate MD5 checksum for given file.

        :param filepath: Full path to file
        :return: Calculated checksum
        """
        with open(str(filepath), "rb") as f:
            bytes_ = f.read()
            checksum = hashlib.md5(bytes_).hexdigest()
            logger.debug(f"Checksum of file {filepath}: {checksum}")
            return checksum

    @staticmethod
    def exit(messages: Messages = "", exit_code: int = 1) -> None:
        """
        Exit from program with message and with given exit code

        :param messages: Message or list of messages to be printed during exit
        :param exit_code: Exit code. 0 means OK, 1 means error (default: 1)
        :return: None
        """
        if messages:
            if type(messages) == str:
                messages = [messages]
            for msg in messages:
                logger.error(msg)
        sys.exit(exit_code)

    @staticmethod
    def setup_dirs(dirs: List[Path]) -> None:
        """
        Create given dirs with all necessary parents

        :param dirs: List of firs to be created
        :return: None
        """
        for dir_ in dirs:
            dir_.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_dir_size(directory: str) -> str:
        """
        Calculate the total size of all files and subdirs of given dir

        :param directory: Path to directory
        :return: Formatted size of dir e.g. 1.22 KB, 4.9 GB
        """
        byte_size = sum(f.lstat().st_size for f in Path(directory).glob("**/*") if f.is_file() and f not in [".", ".."])
        return humanfriendly.format_size(byte_size)

    @staticmethod
    def get_environ_variable(env_name) -> str:
        """
        Get from environment variable value or raise error when not defined.

        :return: Environment variable value
        """
        env_value = os.environ.get(env_name)
        logger.debug(f"{env_name} set to {env_value}")
        if not env_value:
            Support.exit(f"Env variable {env_name} not defined")
        return env_value

    @staticmethod
    def clear_cache() -> None:
        """
        Delete cache directory

        :return: None
        """
        shutil.rmtree(CACHE_DIR, ignore_errors=True)

    @staticmethod
    def get_installed_drivers() -> List[str]:
        """
        Get list of installed drivers from .drivers.ini

        :return: List of installed drivers
        """
        return ConfigObj(str(DRIVERS_CFG)).sections
