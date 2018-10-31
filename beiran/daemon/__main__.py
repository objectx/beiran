"""Main script for beiran daemon"""
from .main import BeiranDaemon
from .common import Services

Services.daemon = BeiranDaemon() # type: ignore
Services.daemon.run() # type: ignore
