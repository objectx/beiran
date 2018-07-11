
import grpc
import time
from concurrent import futures

from api_pb2_grpc import ImageServiceServicer, add_ImageServiceServicer_to_server
from api_pb2 import ImageStatusResponse
from api_pb2 import ListImagesResponse, Image
from api_pb2 import PullImageResponse
from api_pb2 import RemoveImageResponse
from api_pb2 import ImageFsInfoResponse

class K8SImageService(ImageServiceServicer):
    """ImageService defines the public APIs for managing images.
    """

    def add_to_server(server):
        # add_ImageServiceServicer_to_server
        pass

    def ListImages(self, request, context):
        """ListImages lists existing images.
        """

        # https://github.com/containerd/containerd/blob/372cdfac3b9e7fa6e1b21d38b6f84d996b4f4142/api/services/images/v1/images.proto
        # https://github.com/containerd/containerd/blob/1a5e0df98f9673ca37a9018f14e31af9984d49b0/services/images/local.go#L89

        # TODO: Investigate and implement filters
        filters = []
        if request.filter:
            filters = [ request.filter.image.image ]
        elif request.filters:
            filters = request.filters

        images = []
        for image_data in ["hello"]:
            image = Image(id="hello1",
                                    repo_tags=["hello2","hello3"],
                                    repo_digests=["deadbeefdeadbeef","deadbeef"],
                                    size=4873483,
                                    uid=0,
                                    username="root")
            images.append(image)
        response = ListImagesResponse(images=images)
        return response

    def ImageStatus(self, request, context):
        """ImageStatus returns the status of the image. If the image is not
        present, returns a response with ImageStatusResponse.Image set to
        nil.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PullImage(self, request, context):
        """PullImage pulls an image with authentication config.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RemoveImage(self, request, context):
        """RemoveImage removes the image.
        This call is idempotent, and must not return an error if the image has
        already been removed.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ImageFsInfo(self, request, context):
        """ImageFSInfo returns information of the filesystem that is used to store images.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
    add_ImageServiceServicer_to_server(K8SImageService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
            while True:
                    time.sleep(86400)
    except KeyboardInterrupt:
            server.stop(0)

if __name__ == '__main__':
    main()
