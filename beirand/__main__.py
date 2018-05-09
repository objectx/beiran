"""Main script for beiran daemon"""
from .main import BeiranDaemon

THE_DAEMON = BeiranDaemon()
THE_DAEMON.run()
