import logging
import logging.config
import pytz
from datetime import datetime

NY_TZ = pytz.timezone("America/New_York")

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
        "uvicorn_file": {
            "()": OpenCloseFileHandler,
            "filename": "uvicorn_logs.log",
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
        "uvicorn": {
            "handlers": ["uvicorn_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["uvicorn_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["uvicorn_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def timetz(*_):
    return datetime.now(NY_TZ).timetuple()

logger = logging.getLogger("logs")
logging.Formatter.converter = timetz

# Apply logging configuration
logging.config.dictConfig(LOGGING_CONFIG)
