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

import grpc

from beiran_package_container.grpc.images_pb2_grpc import ImagesStub
# from beiran_interface_containerd.api_pb2 import ListImagesRequest

class ImagesClient:
    """This client class communicates with ImagesServicer"""
    def __init__(self, channel: grpc.Channel):
        self.stub = ImagesStub(channel)

    # async def list_images(self, filters: List(str)):
    #     """Send ListImagesRequest to containerd"""
    #     return self.stub.List(
    #         ListImagesRequest(
    #             filters=
    #         )
    #     )
