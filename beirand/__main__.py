"""Main script for beiran daemon"""
from .main import BeiranDaemon
from .common import Services

Services.daemon = BeiranDaemon()
Services.daemon.run()
