"""
k8s interface plugin
"""

from concurrent import futures

import grpc

from beiran.plugin import BaseInterfacePlugin
from beiran.config import config
from .grpc_server import K8SImageServicer
from .api_pb2_grpc import add_ImageServiceServicer_to_server

from .grpc_server import Services as ApiDependencies

PLUGIN_NAME = 'k8s'
PLUGIN_TYPE = 'interface'

# pylint: disable=attribute-defined-outside-init
class K8SInterface(BaseInterfacePlugin):
    """cri support for Beiran"""
    def __init__(self, plugin_config=dict()):
        super().__init__(plugin_config)
        if 'unix_socket_path' in plugin_config:
            self.unix_socket_path = plugin_config['unix_socket_path']
        else:
            self.unix_socket_path = "unix://" + config.run_dir + "/beiran-cri.sock"

    async def init(self):
        ApiDependencies.logger = self.log
        ApiDependencies.loop = self.loop
        ApiDependencies.daemon = self.daemon

        self.servicer = K8SImageServicer()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ImageServiceServicer_to_server(self.servicer, self.server)
        self.server.add_insecure_port(self.unix_socket_path)

    async def start(self):
        """Start gRPC server"""
        self.server.start()

    async def stop(self):
        """Stop gRPC server"""
        self.server.stop(None)
