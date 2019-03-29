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
client of ImageService (cri)
"""

import grpc

from beiran_package_container.grpc.api_pb2_grpc import ImageServiceStub
from beiran_package_container.grpc.api_pb2 import ImageFilter, ImageSpec, AuthConfig
from beiran_package_container.grpc.api_pb2 import ListImagesRequest, ImageStatusRequest, \
                                                PullImageRequest, ImageFsInfoRequest

class ImageServiceClient:
    """This client class communicates with ImageServiceServicer"""
    def __init__(self, channel: grpc.Channel):
        self.stub = ImageServiceStub(channel)

    async def get_all_image_datas(self):
        """
        Get status and configs of all images stored in contrainerd
        """
        response = await self.list_images()
        image_datas = {
            image.id: {
                'repo_tags': list(image.repo_tags), # convert RepeatedScalarContainer to list
                'repo_digests': list(image.repo_digests), # convert RepeatedScalarContainer to list
                'size': image.size
                        # 'uid': image.uid,
                        # 'username': image.username
            }
            for image in response.images
        }

        # get configs
        for image_id in image_datas:
            response = await self.image_status(image_id)
            image_datas[image_id]['config'] = response.info['info']

        return image_datas

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
