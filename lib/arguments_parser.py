import argparse


class ArgumentsParser(argparse.ArgumentParser):
    LEVELS = ["DEBUG", "INFO", "WARNING"]

    def __init__(self) -> None:
        super().__init__(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        self.add_argument('--log-file', type=str, default=None,
                          help="log all messages into the specified file; if not specified, log to stdout")
        self.add_argument('--log-level', type=str, choices=ArgumentsParser.LEVELS, default="WARNING",
                          help='set a level of logging')
        self.add_argument('--dry-run', action='store_true', default=False,
                          help="don't store anything permanently")

    def set_description(self, text: str) -> None:
        self.description = text
