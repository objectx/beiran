
import grpc
import time
import logging
from concurrent import futures

from api_pb2_grpc import ImageServiceServicer, add_ImageServiceServicer_to_server
from api_pb2 import ImageStatusResponse
from api_pb2 import ListImagesResponse, Image
from api_pb2 import PullImageResponse
from api_pb2 import RemoveImageResponse
from api_pb2 import ImageFsInfoResponse, FilesystemUsage, FilesystemIdentifier, UInt64Value

from api_pb2 import Int64Value


class K8SImageServicer(ImageServiceServicer):
    """ImageService defines the public APIs for managing images.
    """
    def ListImages(self, request, context):
        """ListImages lists existing images.
        """
        # https://github.com/containerd/containerd/blob/372cdfac3b9e7fa6e1b21d38b6f84d996b4f4142/api/services/images/v1/images.proto
        # https://github.com/containerd/containerd/blob/1a5e0df98f9673ca37a9018f14e31af9984d49b0/services/images/local.go#L89

        # TODO: Investigate and implement filters
        print("req: ", request)
        print("req.filter: ", request.filter) # ImageFilter
        print("req.filter.image: ", request.filter.image) # ImageSpec
        print("req.filter.image.image: ", request.filter.image.image) # string

        images = []

        # get beiran iamges
        # convert image(dict) to Image
        
        image = Image(
            id="hello1",
            repo_tags=["hello2","hello3"],
            repo_digests=["deadbeefdeadbeef","deadbeef"],
            size=4873483,
            uid=Int64Value(value=1),
            username="hellodesu"
        )
        images.append(image)
        response = ListImagesResponse(images=images)
        return response

    def ImageStatus(self, request, context):
        """ImageStatus returns the status of the image. If the image is not
        present, returns a response with ImageStatusResponse.Image set to
        nil.
        """
        print("req2: ", request)
        print("req2.image: ", request.image)
        print("req2.verbose: ", request.verbose)
        print("req2.image.image: ", request.image.image)

        image = Image(
                id="hello1",
                repo_tags=["hello2","hello3"],
                repo_digests=["deadbeefdeadbeef","deadbeef"],
                size=4873483,
                uid=Int64Value(value=2),
                username="root"
        )
        info = {"HEI": "HEIIII"}
        response = ImageStatusResponse(image=image, info=info)
        return response

    def PullImage(self, request, context):
        """PullImage pulls an image with authentication config.
        """
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
        print("req4: ", request)
        print("req4.image: ", request.image)

        response = RemoveImageResponse()
        return response

    def ImageFsInfo(self, request, context):
        """ImageFSInfo returns information of the filesystem that is used to store images.
        """
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
    add_ImageServiceServicer_to_server(K8SImageServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
            server.stop(0)

if __name__ == '__main__':
    main()
