"""Main script for beiran daemon"""
from . import main

THE_DAEMON = main.BeiranDaemon()
THE_DAEMON.run()
