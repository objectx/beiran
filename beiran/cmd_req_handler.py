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

"""HTTP and WS API implementation of beiran daemon"""
import json
import logging

from typing import Callable, Any
from tornado import httputil

from tornado import web
from tornado.web import MissingArgumentError, HTTPError


LOGGER = logging.getLogger('beiran.cmd_req_handler')


def rpc(func: Callable) -> Callable:
    """
    Mark method as cmd
    Args:
        func: method will be marked as cmd

    Returns:

    """
    func.rpc = True # type: ignore
    return func


class RPCMeta(type):
    """Metaclass which marks public methods and append them into `public_methods` attr while init"""
    def __new__(mcs: type, name: str, bases: tuple, dct: dict) -> "RPCMeta":
        klass = super().__new__(mcs, name, bases, dct)
        klass.public_methods = list() # type: ignore

        for obj_name, obj in dct.items():
            if callable(obj) and hasattr(obj, 'rpc'):
                klass.public_methods.append(obj_name) # type: ignore

        return klass # type: ignore


class JSONEndpoint(web.RequestHandler):
    """Request handler where requests and responses speak JSON."""

    def __init__(self, application: web.Application,
                 request: httputil.HTTPServerRequest,
                 **kwargs: Any) -> None:
        super().__init__(application, request, **kwargs)
        self.json_data = dict() # type: dict
        self.response = dict() # type: dict

    def data_received(self, chunk):
        pass

    def prepare(self) -> None:
        # Incorporate request JSON into arguments dictionary.
        if self.request.body:
            try:
                self.json_data = json.loads(self.request.body)
            except ValueError:
                message = 'Unable to parse JSON.'
                self.send_error(400, message=message) # Bad Request

        # Set up response dictionary.
        self.response = dict()

    def set_default_headers(self) -> None:
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        if 'message' not in kwargs:
            if status_code == 405:
                kwargs['message'] = 'Invalid HTTP method.'
            else:
                kwargs['message'] = 'Unknown error.'

        payload = {}
        for key, value in kwargs.items():
            payload[key] = str(value)
        self.response = payload
        self.write_json()

    def write_json(self) -> None:
        """Write json output"""
        output = json.dumps(self.response)
        self.write(output)


class BaseRPCEndpoint(metaclass=RPCMeta):
    """Base Command Request Handler to be extended"""
    pass


# pylint: disable=no-member
class RPCEndpoint(BaseRPCEndpoint, JSONEndpoint):
    """
    Command Request Handler, overrides Tornado's post method which dispatches cli commands
    to appropriate methods.
    """
    # pylint: disable=arguments-differ
    @web.asynchronous
    async def post(self) -> None:
        """
        Requires `cmd` arguments and checks if it is in available public method list.

        Raises:
            MissingArgumentError: if `cmd` argument is not provided
            HTTPError: if `cmd` is not in allowed methods.

        """

        command = self.get_argument('cmd')

        if not command:
            raise MissingArgumentError('cmd')

        if command not in self.public_methods:
            raise HTTPError(
                400,
                "This endpoint does not implement `{}`. `cmd may be one of those {}".format(
                    command, ', '.join(self.public_methods))
            )

        LOGGER.debug("Node endpoint is invoked with command `%s`", command)
        method = getattr(self, command)
        return await method()
# pylint: enable=no-member
