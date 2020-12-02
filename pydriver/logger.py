import logging
import logging.handlers


class Logger:
    def __init__(self, log_path):
        self._log_path = log_path

    def configure_logging(self):
        # Set up a specific logger with our desired output level
        logger = logging.getLogger("PyDriver")
        logger.setLevel(logging.DEBUG)
        file_handler = logging.handlers.RotatingFileHandler(self._log_path, maxBytes=1024 * 1024 * 10, backupCount=5)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s - %(lineno)s - %(levelname)s - %(funcName)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.info(f"Log file stored in: {self._log_path}")
        return logger
