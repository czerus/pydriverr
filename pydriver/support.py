import hashlib
import logging
import sys
from pathlib import Path
from typing import List, Union

import humanfriendly


class Support:
    def __init__(self):
        self._logger = logging.getLogger("PyDriver")

    def calculate_checksum(self, filepath: Path) -> str:
        with open(str(filepath), "rb") as f:
            bytes_ = f.read()
            checksum = hashlib.md5(bytes_).hexdigest()
            self._logger.debug(f"Checksum of file {filepath}: {checksum}")
            return checksum

    def exit(self, messages: Union[List, str] = "", exit_code: int = 1) -> None:
        if messages:
            if type(messages) == str:
                messages = [messages]
            for msg in messages:
                self._logger.error(msg)
        sys.exit(exit_code)

    @staticmethod
    def setup_dirs(dirs: List[Path]):
        for dir_ in dirs:
            dir_.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_dir_size(startdir: Path) -> str:
        byte_size = sum(f.lstat().st_size for f in startdir.glob("**/*") if f.is_file() and f not in [".", ".."])
        return humanfriendly.format_size(byte_size)
