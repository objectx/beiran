"""HTTP and WS API implementation of beiran daemon"""
import json
from tornado import web
from tornado.web import MissingArgumentError
from beirand.common import Services


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

        for name, obj in dct.items():
            if callable(obj) and hasattr(obj, 'cmd'):
                klass.public_methods.append(obj)

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

        if 'address' not in self.json_data:
            raise Exception("Unacceptable data")

        cmd = self.get_argument('cmd')

        if not cmd:
            raise MissingArgumentError('cmd')

        if cmd not in self.public_methods:
            raise NotImplementedError("This endpoint does not implement `{}`"
                                          .format(cmd))

        Services.logger.debug("Node endpoint is invoked with command `%s`", cmd)
        method = getattr(self, cmd)
        return await method()
