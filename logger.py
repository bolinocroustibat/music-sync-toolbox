import logging
import logging.handlers
from pathlib import Path


class FileLogger:
    WHITE = "\033[97m"
    PURPLE = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def __init__(self, log_file: Path) -> None:
        # logger
        # one logger per file, so messages only land in their own log file
        self.logger = logging.getLogger(f"music_sync.{log_file}")
        self.logger.setLevel(20)
        if self.logger.handlers:
            return

        # handler
        five_mbytes = 10**6 * 5
        handler = logging.handlers.RotatingFileHandler(
            str(log_file), maxBytes=five_mbytes, encoding="UTF-8", backupCount=0
        )
        handler.setLevel(20)

        # create formater
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"
        )

        # add formater to handler
        handler.setFormatter(formatter)

        # add handler to logger
        self.logger.addHandler(handler)

    def log(self, message: str) -> None:
        print(f"{self.WHITE}{message}{self.ENDC}")
        self.logger.info(message)

    def info(self, message: str) -> None:
        print(f"{self.PURPLE}{message}{self.ENDC}")
        self.logger.info(message)

    def debug(self, message: str) -> None:
        print(f"{self.CYAN}{message}{self.ENDC}")
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        print(f"{self.YELLOW}{message}{self.ENDC}")
        self.logger.warning(message)

    def error(self, message: str) -> None:
        print(f"{self.RED}{message}{self.ENDC}")
        self.logger.error(message)

    def success(self, message: str) -> None:
        print(f"{self.GREEN}{message}{self.ENDC}")
        self.logger.info(message)
