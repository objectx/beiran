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
containerd interface plugin
"""
import grpc

from beiran.plugin import BaseInterfacePlugin
from beiran_interface_containerd.api_pb2_grpc import ImageServiceStub
from beiran_interface_containerd.api_pb2 import ImageFilter, ImageSpec, AuthConfig
from beiran_interface_containerd.api_pb2 import ListImagesRequest, ImageStatusRequest, \
                                                PullImageRequest, ImageFsInfoRequest

PLUGIN_NAME = 'containerd'
PLUGIN_TYPE = 'interface'

# pylint: disable=attribute-defined-outside-init
class ContainerdInterface(BaseInterfacePlugin):
    """Containerd support for Beiran"""
    DEFAULTS = {
        'containerd_socket_path': "unix:///run/containerd/containerd.sock"
    }

    async def init(self):
        channel = grpc.insecure_channel(self.config['containerd_socket_path'])
        self.stub = ImageServiceStub(channel)

        # get storage path
        response = await self.image_fs_info()
        self.storage_path = response.image_filesystems[0].fs_id.mountpoint

    async def start(self):
        # await self.list_images()
        # print(await self.image_status("docker.io/library/redis:latest"))
        # print(await self.pull_image("docker.io/library/nginx:latest"))
        pass


    async def stop(self):
        pass

    async def list_images(self, image: str = None):
        """Send ListImagesRequest to containerd"""
        return self.stub.ListImages(
            ListImagesRequest(
                filter=ImageFilter(
                    image=ImageSpec(
                        image=image
                    )
                )
            )
        )

    async def image_status(self, image: str, verbose: bool = True):
        """Send ImageStatusRequest to containerd"""
        return self.stub.ImageStatus(
            ImageStatusRequest(
                image=ImageSpec(
                    image=image
                ),
                verbose=verbose
            )
        )

    async def pull_image(self, image: str, **kwargs):
        """Send PullImageRequest to containerd"""
        return self.stub.PullImage(
            PullImageRequest(
                image=ImageSpec(
                    image=image
                ),
                auth=AuthConfig(
                    **kwargs
                )
            )
            # sandbox_config=PodSandboxConfig # not support
        )

    async def image_fs_info(self):
        """Send ImageFsInfoRequest to containerd"""
        return self.stub.ImageFsInfo(
            ImageFsInfoRequest()
        )

