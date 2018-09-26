"""
gRPC server (CRI Version: v1alpha2)
"""



import json
import random
import asyncio
import grpc

import aiohttp
from peewee import SQL

from beiran.client import Client
from beiran.util import run_in_loop
from plugins.beiran_package_docker.models import DockerImage

from .api_pb2_grpc import ImageServiceServicer, ImageServiceStub
from .api_pb2 import ImageStatusResponse
from .api_pb2 import ListImagesResponse, Image
from .api_pb2 import PullImageResponse
from .api_pb2 import RemoveImageResponse
from .api_pb2 import ImageFsInfoResponse, FilesystemUsage, FilesystemIdentifier, UInt64Value
from .api_pb2 import Int64Value

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

        for image in DockerImage.select():
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

        # This is for supporting RepoDigest included in request message.
        # RepoDigest is a string value and includes @
        # (e.g. docker.io/library/redis@sha256:61e089bc75e6bd6650a63d8962e3601698115fee26ada4ff1b166b37bf7a7153) # pylint: disable=line-too-long
        if "@" in request.image.image:
            images = DockerImage.select()
            images = images.where(SQL('repo_digests LIKE \'%%"%s"%%\'' % request.image.image))
            image = images.first()

        elif request.image.image.startswith("sha256:"):
            image = DockerImage.get(DockerImage.hash_id == request.image.image)

        else:
            image_name = request.image.image
            if ":" not in image_name:
                image_name += ":latest"

            images = DockerImage.select()
            images = images.where(SQL('tags LIKE \'%%"%s"%%\'' % image_name))
            image = images.first()

        if not image:
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
        # Can not pull an image from registry server.
        Services.logger.debug("request: PullImage")

        if not self.check_plugin_timeout('package:docker', context):
            return PullImageResponse()

        image_name = request.image.image
        if ":" not in image_name:
            image_name += ":latest"

        try:
            # not supporting AuthConfig and PodSandboxConfig now
            image_ref = run_in_loop(self.pull_routine(image_name),
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


    async def pull_routine(self, image_name): # pylint: disable=too-many-locals
        """coroutine for pulling images"""
        available_nodes = await DockerImage.get_available_nodes_by_tag(image_name)
        online_nodes = Services.daemon.nodes.all_nodes.keys()
        online_availables = [n for n in available_nodes if n in online_nodes]
        if online_availables:
            node_identifier = random.choice(online_availables)

        query = DockerImage.select()
        query = query.where(SQL('tags LIKE \'%%"%s"%%\'' % image_name))
        image = query.first()

        Services.logger.debug("Will fetch %s from >>%s<<",
                              image_name, node_identifier)
        node = await Services.daemon.nodes.get_node_by_uuid(node_identifier)

        client = Client(node=node)
        chunks = asyncio.Queue()

        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        try:
            # pylint: disable=no-value-for-parameter,no-member
            docker_future = Services.aiodocker.images.import_image(data=sender(chunks))
            # pylint: enable=no-value-for-parameter,no-member
            docker_result = asyncio.ensure_future(docker_future)

            image_response = await client.stream_image(image_name)
            async for data in image_response.content.iter_chunked(64*1024):
                # Services.logger.debug("Pull: Chunk received with length: %s", len(data))
                chunks.put_nowait(data)

            chunks.put_nowait(None)

            await docker_result
        except Client.Error as error:
            Services.logger.error(error)

        return image.hash_id


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
