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
client of Images
"""

from typing import List
import grpc

from beiran_package_container.grpc.images_pb2_grpc import ImagesStub
from beiran_package_container.grpc.images_pb2 import ListImagesRequest

CONTAINERD_NAMESPACE_KEY = 'containerd-namespace'
CONTAINERD_NAMESPACE_VALUE = 'default'

class ImagesClient:
    """This client class communicates with ImagesServicer"""
    def __init__(self, channel: grpc.Channel):
        self.stub = ImagesStub(channel)
        self.namespace = (CONTAINERD_NAMESPACE_KEY, CONTAINERD_NAMESPACE_VALUE)
    
    def set_namespace(self, namespace: str):
        """Set new namespace"""
        self.namespace = (CONTAINERD_NAMESPACE_KEY, namespace)
    
    @property
    def metadata(self) -> list:
        """Create new metadata"""
        return [self.namespace]


    async def list_images(self, filters: List[str] = None):
        """Send ListImagesRequest to containerd"""
        return self.stub.List(
            ListImagesRequest(
                filters=filters
            ),
            metadata=self.metadata
        )
