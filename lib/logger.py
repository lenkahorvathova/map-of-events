import logging
import sys


def set_up_script_logger(script_name: str, log_file: str = None, log_level: str = "WARNING") -> logging.LoggerAdapter:
    logger = logging.getLogger(script_name)
    if script_name[-3:] == ".py":
        script_name = script_name[:-3].replace('/', '.')
    extra = {'scriptName': script_name}
    log_format = "%(asctime)s - %(scriptName)s.%(funcName)s:%(lineno)s - %(levelname)s: %(message)s"
    logger = _set_up_logger(logger, log_format, log_file, log_level)
    return logging.LoggerAdapter(logger, extra)


def set_up_simple_logger(function_name: str, log_file: str = None, log_level: str = "WARNING") -> logging.Logger:
    logger = logging.getLogger(function_name)
    log_format = "%(funcName)s - %(levelname)s: %(message)s"
    return _set_up_logger(logger, log_format, log_file, log_level)


def _set_up_logger(logger: logging.Logger, log_format: str, log_file: str = None,
                   log_level: str = "WARNING") -> logging.Logger:
    handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(log_format)
    if log_level == "DEBUG":
        level = logging.DEBUG
    elif log_level == "INFO":
        level = logging.INFO
    else:
        level = logging.WARNING

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger
