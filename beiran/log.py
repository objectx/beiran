""" Logging package for daemon """

import os
import sys
import logging

def build_logger(filename, log_level=logging.DEBUG):
    """ Build logger class for module """
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [stdout_handler]
    if filename:
        file_handler = logging.FileHandler(filename=os.getenv(
            'LOG_FILE', filename))
        handlers.append(file_handler)
    logging.getLogger('asyncio').level = logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(name)s] %(levelname)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__package__)
