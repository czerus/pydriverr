import hashlib
import sys
from pathlib import Path
from typing import List

import humanfriendly

from ciyen.ciyen_types import Messages
from ciyen.custom_logger import logger


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
    def calculate_dir_size(directory: Path) -> str:
        """
        Calculate the total size of all files and subdirs of given dir

        :param directory: Path to directory
        :return: Formatted size of dir e.g. 1.22 KB, 4.9 GB
        """
        byte_size = sum(f.lstat().st_size for f in directory.glob("**/*") if f.is_file() and f not in [".", ".."])
        return humanfriendly.format_size(byte_size)
