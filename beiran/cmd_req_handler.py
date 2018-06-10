"""HTTP and WS API implementation of beiran daemon"""
import json
import logging
from tornado import web
from tornado.web import MissingArgumentError, HTTPError


logger = logging.getLogger('beiran.cmd_req_handler')


def cmd(func):
    """
    Mark method as cmd
    Args:
        func: method will be marked as cmd

    Returns:

    """
    func.cmd = True
    return func


class CMDMeta(type):
    def __new__(cls, name, bases, dct):
        klass = super().__new__(cls, name, bases, dct)
        klass.public_methods = list()

        for obj_name, obj in dct.items():
            if callable(obj) and hasattr(obj, 'cmd'):
                klass.public_methods.append(obj_name)

        return klass


class JsonHandler(web.RequestHandler):
    """Request handler where requests and responses speak JSON."""

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.json_data = dict()
        self.response = dict()

    def data_received(self, chunk):
        pass

    def prepare(self):
        # Incorporate request JSON into arguments dictionary.
        if self.request.body:
            try:
                self.json_data = json.loads(self.request.body)
            except ValueError:
                message = 'Unable to parse JSON.'
                self.send_error(400, message=message) # Bad Request

        # Set up response dictionary.
        self.response = dict()

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code, **kwargs):
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

    def write_json(self):
        """Write json output"""
        output = json.dumps(self.response)
        self.write(output)


class BaseCmdRequestHandler(metaclass=CMDMeta):
    pass


class CmdRequestHandler(BaseCmdRequestHandler, JsonHandler):
    # pylint: disable=arguments-differ
    @web.asynchronous
    async def post(self):

        command = self.get_argument('cmd')

        if not command:
            raise MissingArgumentError('cmd')

        if command not in self.public_methods:
            raise HTTPError(
                400,
                "This endpoint does not implement `{}`. `cmd may be one of those {}".format(
                    command, ', '.join(self.public_methods))
            )

        logger.debug("Node endpoint is invoked with command `%s`", command)
        method = getattr(self, command)
        return await method()
