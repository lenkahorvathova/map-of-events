import logging
import sys


def set_up_script_logger(script_name: str, log_file: str = None, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger(script_name[:-3].replace('/', '.'))
    log_format = "%(asctime)s - %(name)s.%(funcName)s:%(lineno)s - %(levelname)s: %(message)s"

    return set_up_logger(logger, log_format, log_file, debug)


def set_up_simple_logger(function_name: str, log_file: str = None, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger(function_name)
    log_format = "...%(funcName)s - %(levelname)s: %(message)s"

    return set_up_logger(logger, log_format, log_file, debug)


def set_up_logger(logger: logging.Logger, log_format: str, log_file: str = None, debug: bool = False) -> logging.Logger:
    handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler(sys.stdout)
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(log_format)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger
