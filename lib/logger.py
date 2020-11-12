import logging
import sys


def set_up_logger(script_name: str, log_file: str = None, debug: bool = False) -> object:
    logger = logging.getLogger(script_name[:-3].replace('/', '.'))

    handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler(sys.stdout)
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter("%(asctime)s - %(name)s.%(funcName)s:%(lineno)s - %(levelname)s: %(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger
