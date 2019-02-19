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
    """CRI v1alpha2 support for Beiran"""
    DEFAULTS = {} # type: dict

    def __init__(self, plugin_config: dict) -> None:
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
