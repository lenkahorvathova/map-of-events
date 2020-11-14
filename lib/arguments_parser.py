import argparse


class ArgumentsParser(argparse.ArgumentParser):
    def __init__(self) -> None:
        super().__init__(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        self.add_argument('--log-file', type=str, default=None,
                          help="log all messages into the specified file; if not specified, log to stdout")
        self.add_argument('--debug', action='store_true', default=False,
                          help="set a logging level to DEBUG; if not specified, set a level as INFO")
        self.add_argument('--dry-run', action='store_true', default=False,
                          help="don't store anything permanently")
