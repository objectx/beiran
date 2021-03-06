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
gRPC server (CRI Version: v1alpha2)
"""



import json
import asyncio
import grpc

from beiran.util import run_in_loop
from beiran_package_container.models import ContainerImage
from beiran_package_container.grpc.api_pb2_grpc import ImageServiceServicer, ImageServiceStub
from beiran_package_container.grpc.api_pb2 import Image, FilesystemUsage, FilesystemIdentifier, \
                                                  UInt64Value, Int64Value
from beiran_package_container.grpc.api_pb2 import ImageStatusResponse, ListImagesResponse, \
                                                  PullImageResponse, RemoveImageResponse, \
                                                  ImageFsInfoResponse

from beiran_interface_docker.api import ImageList


class Services:
    """These needs to be injected from the plugin init code"""
    loop = None
    logger = None
    daemon = None
    aiodocker = None

def get_username_or_uid(username: str):
    """
    get username or uid of the image user
    If username is numeric, it will be treated as uid; or else, it is treated as user name.
    """
    if username == "":
        return None, ""

    username = username.split(":")[0]
    try:
        uid = Int64Value(value=int(username))
        return uid, ""
    except ValueError:
        return None, username


class K8SImageServicer(ImageServiceServicer):
    """ImageService defines the public APIs for managing images.
    """
    TIMEOUT_SEC = 5

    def __init__(self):
        self.cri_fw = CRIForwarder()

    def ListImages(self, request, context):
        """ListImages lists existing images.
        """
        Services.logger.debug("request: ListImages")
        # don't care ImageFilter like containerd (containerd/cri/pkg/server/image_list.go)

        if not self.check_plugin_timeout('package:docker', context):
            return ListImagesResponse()

        images = []

        for image in ContainerImage.select():
            uid, username = get_username_or_uid(image.config["User"])

            images.append(Image(
                id=image.hash_id,
                repo_tags=image.tags,
                repo_digests=image.repo_digests,
                size=image.size,
                uid=uid,
                username=username
            ))

        response = ListImagesResponse(images=images)
        return response

    def ImageStatus(self, request, context):
        """ImageStatus returns the status of the image. If the image is not
        present, returns a response with ImageStatusResponse.Image set to
        nil.
        """
        Services.logger.debug("request: ImageStatus")

        if not self.check_plugin_timeout('package:docker', context):
            return ImageStatusResponse()

        if not request.image:
            return ImageStatusResponse()

        try:
            image = ContainerImage.get_image_data(request.image.image)
        except ContainerImage.DoesNotExist:
            return ImageStatusResponse()

        info = {}
        if request.verbose:
            info = {'config': json.dumps(image.config)} # tentatively return config...

        uid, username = get_username_or_uid(image.config["User"])

        response = ImageStatusResponse(image=Image(
            id=image.hash_id,
            repo_tags=image.tags,
            repo_digests=image.repo_digests,
            size=image.size,
            uid=uid,
            username=username
        ), info=info)
        return response

    def PullImage(self, request, context):
        """PullImage pulls an image with authentication config.
        """
        # This method operates like "beiran image pull".
        Services.logger.debug("request: PullImage")

        if not self.check_plugin_timeout('package:docker', context):
            return PullImageResponse()

        try:
            # not supporting AuthConfig and PodSandboxConfig now
            image_ref = run_in_loop(ImageList.pull_routine(request.image.image),
                                    loop=Services.loop,
                                    sync=True)
            response = PullImageResponse(image_ref=image_ref)
        except Exception: # pylint: disable=broad-except
            try:
                Services.logger.debug("forward a pull request to other CRI endpoint")
                response = self.cri_fw.PullImage(request)
            except grpc._channel._Rendezvous: # pylint: disable=protected-access
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("request was forwarded but the endpoint is unavailable (%s)"
                                    % self.cri_fw.url)
                response = PullImageResponse()

        return response

    def RemoveImage(self, request, context):
        """RemoveImage removes the image.
        This call is idempotent, and must not return an error if the image has
        already been removed.
        """
        Services.logger.debug("request: RemoveImage")

        if not self.check_plugin_timeout('package:docker', context):
            return RemoveImageResponse()

        # not support

        response = RemoveImageResponse()
        return response

    def ImageFsInfo(self, request, context):
        """ImageFSInfo returns information of the filesystem that is used to store images.
        """
        Services.logger.debug("request: ImageFsInfo")

        if not self.check_plugin_timeout('package:docker', context):
            return RemoveImageResponse()

        # not support

        response = ImageFsInfoResponse(
            image_filesystems=FilesystemUsage(
                timestamp=None,
                fs_id=FilesystemIdentifier(),
                used_bytes=UInt64Value(),
                inodes_used=UInt64Value()
            )
        )
        return response

    def check_plugin_timeout(self, plugin_name, context):
        """
        Check and wait until plugin status to be ready.
        If plugin status isn't 'ready', set an error code and a description to the context.
        """
        try:
            Services.daemon.check_wait_plugin_status_ready(plugin_name,
                                                           Services.loop,
                                                           K8SImageServicer.TIMEOUT_SEC)
            return True
        except asyncio.TimeoutError:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Timeout: %s is not ready" % plugin_name)
            return False


class CRIForwarder():
    """Super class for forwarder classes"""
    def __init__(self, url='unix:///var/run/dockershim.sock'):
        self.url = url

    def PullImage(self, request): # pylint: disable=invalid-name
        """Send PullImageRequest to CRI service"""
        channel = grpc.insecure_channel(self.url)
        stub = ImageServiceStub(channel)
        response = stub.PullImage(request)
        return response
