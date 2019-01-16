# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Logging package for daemon """

import os
import sys
import logging

from typing import List, Union # pylint: disable=unused-import


def build_logger(filename: str = None, log_level: int = logging.ERROR) -> logging.Logger:
    """ Build logger class for module """
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [stdout_handler] # type: List[Union[logging.FileHandler, logging.StreamHandler]]
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
