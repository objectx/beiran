
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

        for resp_image in self.client.get_images():
            images.append(Image(
                id=resp_image["hash_id"], # should obey the format "docker.io/library/aaaa:latest"?
                repo_tags=resp_image["tags"],
                repo_digests=[], # missing filed
                size=resp_image["size"],
                uid=Int64Value(value=1), # missing field
                username="" # missing field
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


        images = self.client.get_images()
        imagename = request.image.image
        image = None
        find = False

        for resp_image in images:
            # for digest in resp_image["repo_digests"]:
            #     if imagename in digest:
            #         find = True
            #         image = resp_image
            #         break

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
    
        response = ImageStatusResponse(image=Image(
            id=image["hash_id"],
            repo_tags=image["tags"],
            repo_digests=[], # missing field
            size=image["size"],
            uid=Int64Value(value=1), # missing field
            username="" # missing field
        ), info=info)
        return response

    def PullImage(self, request, context):
        """PullImage pulls an image with authentication config.
        """
        Services.logger.debug("request: PullImage")
        print("req3: ", request)
        print("req3.image: ", request.image)
        print("req3.auth: ", request.auth)
        print("req3.sandbox_config: ", request.sandbox_config)
        print("req3.sandbox_config.metadata: ", request.sandbox_config.metadata)
        print("req3.sandbox_config.dns_config: ", request.sandbox_config.dns_config)
        print("req3.sandbox_config.port_mappings: ", request.sandbox_config.port_mappings)
        print("req3.sandbox_config.linux: ", request.sandbox_config.linux)

        response = PullImageResponse(image_ref="nginx:latest")
        return response

    def RemoveImage(self, request, context):
        """RemoveImage removes the image.
        This call is idempotent, and must not return an error if the image has
        already been removed.
        """
        Services.logger.debug("request: RemoveImage")

        # remove(request.image.image)

        print("req4: ", request)
        print("req4.image: ", request.image)

        response = RemoveImageResponse()
        return response

    def ImageFsInfo(self, request, context):
        """ImageFSInfo returns information of the filesystem that is used to store images.
        """
        Services.logger.debug("request: ImageFsInfo")
        print("req5: ", request)

        filesystemidentifier = FilesystemIdentifier(
            mountpoint="/home/ubuntu"
        )
        filesystemusage = FilesystemUsage(
            timestamp=123,
            fs_id=filesystemidentifier,
            used_bytes = UInt64Value(1),
            inodes_used = UInt64Value(2)
        )
        image_filesystems = []
        image_filesystems.append(filesystemusage)
        response = ImageFsInfoResponse(image_filesystems=image_filesystems)
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
