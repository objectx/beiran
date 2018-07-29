"""
k8s interface plugin
"""

from concurrent import futures

import grpc

from aiodocker import Docker
from beiran.plugin import BaseInterfacePlugin
from .grpc_server import K8SImageServicer
from .api_pb2_grpc import add_ImageServiceServicer_to_server

from .grpc_server import Services as ApiDependencies

PLUGIN_NAME = 'k8s'
PLUGIN_TYPE = 'interface'

# pylint: disable=attribute-defined-outside-init
class K8SInterface(BaseInterfacePlugin):
    """cri support for Beiran"""
    def __init__(self, config):
        super().__init__(config)
        self.unix_socket_path = config['unix_socket_path']

    async def init(self):
        ApiDependencies.logger = self.log
        ApiDependencies.loop = self.loop
        ApiDependencies.daemon = self.daemon
        ApiDependencies.aiodocker = Docker()

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