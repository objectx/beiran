
import grpc
import time
import logging
import os
from concurrent import futures

from api_pb2_grpc import ImageServiceServicer, add_ImageServiceServicer_to_server
from api_pb2 import ImageStatusResponse
from api_pb2 import ListImagesResponse, Image
from api_pb2 import PullImageResponse
from api_pb2 import RemoveImageResponse
from api_pb2 import ImageFsInfoResponse, FilesystemUsage, FilesystemIdentifier, UInt64Value

from api_pb2 import Int64Value

from beiran.sync_client import Client
from beirand.common import Services


def get_user_from_image(username: str):
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
    def __init__(self, url):
        super().__init__()
        self.client = Client(url)

    def ListImages(self, request, context):
        """ListImages lists existing images.
        """
        # don't care ImageFilter like containerd (https://github.com/containerd/cri/blob/013ab03a5369fa1c75da350ca0888017dc3a3b01/pkg/server/image_list.go#L29)
        Services.logger.debug("request: ListImages")

        images = []

        for image in self.client.get_images():
            uid, username = get_user_from_image(image["config"]["User"])
            
            images.append(Image(
                id=image["hash_id"],
                repo_tags=image["tags"],
                repo_digests=image["repo_digests"],
                size=image["size"],
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

        # if ImageSpec is not set 
        if request.image == None:
            return ImageStatusResponse()

        imagename = request.image.image
        if ":" not in imagename:
            imagename += ":latest"

        images = self.client.get_images()
        image = None
        find = False

        for resp_image in images:
            for digest in resp_image["repo_digests"]:
                if imagename in digest:
                    find = True
                    image = resp_image
                    break

            for tag in resp_image["tags"]:
                if imagename in tag:
                    find = True
                    image = resp_image
                    break

            if imagename in resp_image["hash_id"]:
                find = True
                image = resp_image

            if find:
                break

        info = {}
        if request.verbose:
            # not yet support
            info = {}

        uid, username = get_user_from_image(image["config"]["User"])

        response = ImageStatusResponse(image=Image(
            id=image["hash_id"],
            repo_tags=image["tags"],
            repo_digests=image["repo_digests"],
            size=image["size"],
            uid=uid,
            username=username
        ), info=info)
        return response

    def PullImage(self, request, context):
        """PullImage pulls an image with authentication config.
        """
        # This method operates like "beiran image pull".
        # Do not pull an image from registry server.
        
        Services.logger.debug("request: PullImage")

        imagename = request.image.image
        if ":" not in imagename:
            imagename += ":latest"

        # not supporting AuthConfig and PodSandboxConfig now

        resp = self.client.pull_image(imagename, wait=True)
        image_ref = ""
        images = self.client.get_images()
        for image in images:
            for tag in image["tags"]:
                if tag == imagename:
                    image_ref = image["hash_id"]
                    break
        response = PullImageResponse(image_ref=image_ref)
        return response

    def RemoveImage(self, request, context):
        """RemoveImage removes the image.
        This call is idempotent, and must not return an error if the image has
        already been removed.
        """
        Services.logger.debug("request: RemoveImage")

        # "remove function" isn't implemented yet

        response = RemoveImageResponse()
        return response

    def ImageFsInfo(self, request, context):
        """ImageFSInfo returns information of the filesystem that is used to store images.
        """
        Services.logger.debug("request: ImageFsInfo")

        # not support

        response = ImageFsInfoResponse()
        return response

class MyInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        print(handler_call_details)
        return continuation(handler_call_details)
 


def main():
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=[ MyInterceptor() ])
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    url = "http://localhost:8888" # url for creating sync_client

    add_ImageServiceServicer_to_server(K8SImageServicer(url), server)
    
    # server.add_insecure_port('[::]:50051')
    path = os.getcwd()
    server.add_insecure_port('unix://' + path + "/grpc.sock")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
            server.stop(0)

if __name__ == '__main__':
    main()
