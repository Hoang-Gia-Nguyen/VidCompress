import logging
import sys


def setup_logger(name: str = "transcode-app", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (Optional, could be added if requested)
        # file_handler = logging.FileHandler("app.log")
        # file_handler.setFormatter(formatter)
        # logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()
