import logging
import logging.config
import pytz
from datetime import datetime

CST_TZ = pytz.timezone("America/Chicago")

class OpenCloseFileHandler(logging.FileHandler):
    def emit(self, record):
        self.acquire()
        try:
            with open(self.baseFilename, 'a', encoding=self.encoding) as f:
                msg = self.format(record)
                f.write(msg + self.terminator)
        finally:
            self.release()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "file": {
            "()": OpenCloseFileHandler,
            "filename": "logs.log",
            "formatter": "default",
            "mode": "a",
            "encoding": "utf-8",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "ibapi.utils": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.client": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.connection": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.reader": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "urllib3.connectionpool": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.comm": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.decoder": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "ibapi.wrapper": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

def timetz(*_):
    return datetime.now(CST_TZ).timetuple()

logger = logging.getLogger("logs")
logging.Formatter.converter = timetz

# Apply logging configuration
logging.config.dictConfig(LOGGING_CONFIG)
