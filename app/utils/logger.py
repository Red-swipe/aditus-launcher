import logging


class Logger:
    def __init__(self, name: str = "Aditus"):
        self._log = logging.getLogger(name)

    def debug(self, msg: str) -> None:
        self._log.debug(msg)

    def info(self, msg: str) -> None:
        self._log.info(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)

    def exception(self, msg: str) -> None:
        self._log.exception(msg)
