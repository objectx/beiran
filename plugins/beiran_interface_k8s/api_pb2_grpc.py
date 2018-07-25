# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from plugins.beiran_interface_k8s import api_pb2 as api__pb2

class RuntimeServiceStub(object):
  """Runtime service defines the public APIs for remote container runtimes
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.Version = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/Version',
        request_serializer=api__pb2.VersionRequest.SerializeToString,
        response_deserializer=api__pb2.VersionResponse.FromString,
        )
    self.RunPodSandbox = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/RunPodSandbox',
        request_serializer=api__pb2.RunPodSandboxRequest.SerializeToString,
        response_deserializer=api__pb2.RunPodSandboxResponse.FromString,
        )
    self.StopPodSandbox = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/StopPodSandbox',
        request_serializer=api__pb2.StopPodSandboxRequest.SerializeToString,
        response_deserializer=api__pb2.StopPodSandboxResponse.FromString,
        )
    self.RemovePodSandbox = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/RemovePodSandbox',
        request_serializer=api__pb2.RemovePodSandboxRequest.SerializeToString,
        response_deserializer=api__pb2.RemovePodSandboxResponse.FromString,
        )
    self.PodSandboxStatus = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/PodSandboxStatus',
        request_serializer=api__pb2.PodSandboxStatusRequest.SerializeToString,
        response_deserializer=api__pb2.PodSandboxStatusResponse.FromString,
        )
    self.ListPodSandbox = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ListPodSandbox',
        request_serializer=api__pb2.ListPodSandboxRequest.SerializeToString,
        response_deserializer=api__pb2.ListPodSandboxResponse.FromString,
        )
    self.CreateContainer = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/CreateContainer',
        request_serializer=api__pb2.CreateContainerRequest.SerializeToString,
        response_deserializer=api__pb2.CreateContainerResponse.FromString,
        )
    self.StartContainer = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/StartContainer',
        request_serializer=api__pb2.StartContainerRequest.SerializeToString,
        response_deserializer=api__pb2.StartContainerResponse.FromString,
        )
    self.StopContainer = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/StopContainer',
        request_serializer=api__pb2.StopContainerRequest.SerializeToString,
        response_deserializer=api__pb2.StopContainerResponse.FromString,
        )
    self.RemoveContainer = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/RemoveContainer',
        request_serializer=api__pb2.RemoveContainerRequest.SerializeToString,
        response_deserializer=api__pb2.RemoveContainerResponse.FromString,
        )
    self.ListContainers = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ListContainers',
        request_serializer=api__pb2.ListContainersRequest.SerializeToString,
        response_deserializer=api__pb2.ListContainersResponse.FromString,
        )
    self.ContainerStatus = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ContainerStatus',
        request_serializer=api__pb2.ContainerStatusRequest.SerializeToString,
        response_deserializer=api__pb2.ContainerStatusResponse.FromString,
        )
    self.UpdateContainerResources = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/UpdateContainerResources',
        request_serializer=api__pb2.UpdateContainerResourcesRequest.SerializeToString,
        response_deserializer=api__pb2.UpdateContainerResourcesResponse.FromString,
        )
    self.ReopenContainerLog = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ReopenContainerLog',
        request_serializer=api__pb2.ReopenContainerLogRequest.SerializeToString,
        response_deserializer=api__pb2.ReopenContainerLogResponse.FromString,
        )
    self.ExecSync = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ExecSync',
        request_serializer=api__pb2.ExecSyncRequest.SerializeToString,
        response_deserializer=api__pb2.ExecSyncResponse.FromString,
        )
    self.Exec = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/Exec',
        request_serializer=api__pb2.ExecRequest.SerializeToString,
        response_deserializer=api__pb2.ExecResponse.FromString,
        )
    self.Attach = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/Attach',
        request_serializer=api__pb2.AttachRequest.SerializeToString,
        response_deserializer=api__pb2.AttachResponse.FromString,
        )
    self.PortForward = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/PortForward',
        request_serializer=api__pb2.PortForwardRequest.SerializeToString,
        response_deserializer=api__pb2.PortForwardResponse.FromString,
        )
    self.ContainerStats = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ContainerStats',
        request_serializer=api__pb2.ContainerStatsRequest.SerializeToString,
        response_deserializer=api__pb2.ContainerStatsResponse.FromString,
        )
    self.ListContainerStats = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/ListContainerStats',
        request_serializer=api__pb2.ListContainerStatsRequest.SerializeToString,
        response_deserializer=api__pb2.ListContainerStatsResponse.FromString,
        )
    self.UpdateRuntimeConfig = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/UpdateRuntimeConfig',
        request_serializer=api__pb2.UpdateRuntimeConfigRequest.SerializeToString,
        response_deserializer=api__pb2.UpdateRuntimeConfigResponse.FromString,
        )
    self.Status = channel.unary_unary(
        '/runtime.v1alpha2.RuntimeService/Status',
        request_serializer=api__pb2.StatusRequest.SerializeToString,
        response_deserializer=api__pb2.StatusResponse.FromString,
        )


class RuntimeServiceServicer(object):
  """Runtime service defines the public APIs for remote container runtimes
  """

  def Version(self, request, context):
    """Version returns the runtime name, runtime version, and runtime API version.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RunPodSandbox(self, request, context):
    """RunPodSandbox creates and starts a pod-level sandbox. Runtimes must ensure
    the sandbox is in the ready state on success.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def StopPodSandbox(self, request, context):
    """StopPodSandbox stops any running process that is part of the sandbox and
    reclaims network resources (e.g., IP addresses) allocated to the sandbox.
    If there are any running containers in the sandbox, they must be forcibly
    terminated.
    This call is idempotent, and must not return an error if all relevant
    resources have already been reclaimed. kubelet will call StopPodSandbox
    at least once before calling RemovePodSandbox. It will also attempt to
    reclaim resources eagerly, as soon as a sandbox is not needed. Hence,
    multiple StopPodSandbox calls are expected.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RemovePodSandbox(self, request, context):
    """RemovePodSandbox removes the sandbox. If there are any running containers
    in the sandbox, they must be forcibly terminated and removed.
    This call is idempotent, and must not return an error if the sandbox has
    already been removed.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def PodSandboxStatus(self, request, context):
    """PodSandboxStatus returns the status of the PodSandbox. If the PodSandbox is not
    present, returns an error.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ListPodSandbox(self, request, context):
    """ListPodSandbox returns a list of PodSandboxes.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def CreateContainer(self, request, context):
    """CreateContainer creates a new container in specified PodSandbox
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def StartContainer(self, request, context):
    """StartContainer starts the container.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def StopContainer(self, request, context):
    """StopContainer stops a running container with a grace period (i.e., timeout).
    This call is idempotent, and must not return an error if the container has
    already been stopped.
    TODO: what must the runtime do after the grace period is reached?
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RemoveContainer(self, request, context):
    """RemoveContainer removes the container. If the container is running, the
    container must be forcibly removed.
    This call is idempotent, and must not return an error if the container has
    already been removed.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ListContainers(self, request, context):
    """ListContainers lists all containers by filters.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ContainerStatus(self, request, context):
    """ContainerStatus returns status of the container. If the container is not
    present, returns an error.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UpdateContainerResources(self, request, context):
    """UpdateContainerResources updates ContainerConfig of the container.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ReopenContainerLog(self, request, context):
    """ReopenContainerLog asks runtime to reopen the stdout/stderr log file
    for the container. This is often called after the log file has been
    rotated. If the container is not running, container runtime can choose
    to either create a new log file and return nil, or return an error.
    Once it returns error, new container log file MUST NOT be created.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ExecSync(self, request, context):
    """ExecSync runs a command in a container synchronously.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Exec(self, request, context):
    """Exec prepares a streaming endpoint to execute a command in the container.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Attach(self, request, context):
    """Attach prepares a streaming endpoint to attach to a running container.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def PortForward(self, request, context):
    """PortForward prepares a streaming endpoint to forward ports from a PodSandbox.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ContainerStats(self, request, context):
    """ContainerStats returns stats of the container. If the container does not
    exist, the call returns an error.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ListContainerStats(self, request, context):
    """ListContainerStats returns stats of all running containers.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UpdateRuntimeConfig(self, request, context):
    """UpdateRuntimeConfig updates the runtime configuration based on the given request.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Status(self, request, context):
    """Status returns the status of the runtime.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_RuntimeServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'Version': grpc.unary_unary_rpc_method_handler(
          servicer.Version,
          request_deserializer=api__pb2.VersionRequest.FromString,
          response_serializer=api__pb2.VersionResponse.SerializeToString,
      ),
      'RunPodSandbox': grpc.unary_unary_rpc_method_handler(
          servicer.RunPodSandbox,
          request_deserializer=api__pb2.RunPodSandboxRequest.FromString,
          response_serializer=api__pb2.RunPodSandboxResponse.SerializeToString,
      ),
      'StopPodSandbox': grpc.unary_unary_rpc_method_handler(
          servicer.StopPodSandbox,
          request_deserializer=api__pb2.StopPodSandboxRequest.FromString,
          response_serializer=api__pb2.StopPodSandboxResponse.SerializeToString,
      ),
      'RemovePodSandbox': grpc.unary_unary_rpc_method_handler(
          servicer.RemovePodSandbox,
          request_deserializer=api__pb2.RemovePodSandboxRequest.FromString,
          response_serializer=api__pb2.RemovePodSandboxResponse.SerializeToString,
      ),
      'PodSandboxStatus': grpc.unary_unary_rpc_method_handler(
          servicer.PodSandboxStatus,
          request_deserializer=api__pb2.PodSandboxStatusRequest.FromString,
          response_serializer=api__pb2.PodSandboxStatusResponse.SerializeToString,
      ),
      'ListPodSandbox': grpc.unary_unary_rpc_method_handler(
          servicer.ListPodSandbox,
          request_deserializer=api__pb2.ListPodSandboxRequest.FromString,
          response_serializer=api__pb2.ListPodSandboxResponse.SerializeToString,
      ),
      'CreateContainer': grpc.unary_unary_rpc_method_handler(
          servicer.CreateContainer,
          request_deserializer=api__pb2.CreateContainerRequest.FromString,
          response_serializer=api__pb2.CreateContainerResponse.SerializeToString,
      ),
      'StartContainer': grpc.unary_unary_rpc_method_handler(
          servicer.StartContainer,
          request_deserializer=api__pb2.StartContainerRequest.FromString,
          response_serializer=api__pb2.StartContainerResponse.SerializeToString,
      ),
      'StopContainer': grpc.unary_unary_rpc_method_handler(
          servicer.StopContainer,
          request_deserializer=api__pb2.StopContainerRequest.FromString,
          response_serializer=api__pb2.StopContainerResponse.SerializeToString,
      ),
      'RemoveContainer': grpc.unary_unary_rpc_method_handler(
          servicer.RemoveContainer,
          request_deserializer=api__pb2.RemoveContainerRequest.FromString,
          response_serializer=api__pb2.RemoveContainerResponse.SerializeToString,
      ),
      'ListContainers': grpc.unary_unary_rpc_method_handler(
          servicer.ListContainers,
          request_deserializer=api__pb2.ListContainersRequest.FromString,
          response_serializer=api__pb2.ListContainersResponse.SerializeToString,
      ),
      'ContainerStatus': grpc.unary_unary_rpc_method_handler(
          servicer.ContainerStatus,
          request_deserializer=api__pb2.ContainerStatusRequest.FromString,
          response_serializer=api__pb2.ContainerStatusResponse.SerializeToString,
      ),
      'UpdateContainerResources': grpc.unary_unary_rpc_method_handler(
          servicer.UpdateContainerResources,
          request_deserializer=api__pb2.UpdateContainerResourcesRequest.FromString,
          response_serializer=api__pb2.UpdateContainerResourcesResponse.SerializeToString,
      ),
      'ReopenContainerLog': grpc.unary_unary_rpc_method_handler(
          servicer.ReopenContainerLog,
          request_deserializer=api__pb2.ReopenContainerLogRequest.FromString,
          response_serializer=api__pb2.ReopenContainerLogResponse.SerializeToString,
      ),
      'ExecSync': grpc.unary_unary_rpc_method_handler(
          servicer.ExecSync,
          request_deserializer=api__pb2.ExecSyncRequest.FromString,
          response_serializer=api__pb2.ExecSyncResponse.SerializeToString,
      ),
      'Exec': grpc.unary_unary_rpc_method_handler(
          servicer.Exec,
          request_deserializer=api__pb2.ExecRequest.FromString,
          response_serializer=api__pb2.ExecResponse.SerializeToString,
      ),
      'Attach': grpc.unary_unary_rpc_method_handler(
          servicer.Attach,
          request_deserializer=api__pb2.AttachRequest.FromString,
          response_serializer=api__pb2.AttachResponse.SerializeToString,
      ),
      'PortForward': grpc.unary_unary_rpc_method_handler(
          servicer.PortForward,
          request_deserializer=api__pb2.PortForwardRequest.FromString,
          response_serializer=api__pb2.PortForwardResponse.SerializeToString,
      ),
      'ContainerStats': grpc.unary_unary_rpc_method_handler(
          servicer.ContainerStats,
          request_deserializer=api__pb2.ContainerStatsRequest.FromString,
          response_serializer=api__pb2.ContainerStatsResponse.SerializeToString,
      ),
      'ListContainerStats': grpc.unary_unary_rpc_method_handler(
          servicer.ListContainerStats,
          request_deserializer=api__pb2.ListContainerStatsRequest.FromString,
          response_serializer=api__pb2.ListContainerStatsResponse.SerializeToString,
      ),
      'UpdateRuntimeConfig': grpc.unary_unary_rpc_method_handler(
          servicer.UpdateRuntimeConfig,
          request_deserializer=api__pb2.UpdateRuntimeConfigRequest.FromString,
          response_serializer=api__pb2.UpdateRuntimeConfigResponse.SerializeToString,
      ),
      'Status': grpc.unary_unary_rpc_method_handler(
          servicer.Status,
          request_deserializer=api__pb2.StatusRequest.FromString,
          response_serializer=api__pb2.StatusResponse.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'runtime.v1alpha2.RuntimeService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))


class ImageServiceStub(object):
  """ImageService defines the public APIs for managing images.
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.ListImages = channel.unary_unary(
        '/runtime.v1alpha2.ImageService/ListImages',
        request_serializer=api__pb2.ListImagesRequest.SerializeToString,
        response_deserializer=api__pb2.ListImagesResponse.FromString,
        )
    self.ImageStatus = channel.unary_unary(
        '/runtime.v1alpha2.ImageService/ImageStatus',
        request_serializer=api__pb2.ImageStatusRequest.SerializeToString,
        response_deserializer=api__pb2.ImageStatusResponse.FromString,
        )
    self.PullImage = channel.unary_unary(
        '/runtime.v1alpha2.ImageService/PullImage',
        request_serializer=api__pb2.PullImageRequest.SerializeToString,
        response_deserializer=api__pb2.PullImageResponse.FromString,
        )
    self.RemoveImage = channel.unary_unary(
        '/runtime.v1alpha2.ImageService/RemoveImage',
        request_serializer=api__pb2.RemoveImageRequest.SerializeToString,
        response_deserializer=api__pb2.RemoveImageResponse.FromString,
        )
    self.ImageFsInfo = channel.unary_unary(
        '/runtime.v1alpha2.ImageService/ImageFsInfo',
        request_serializer=api__pb2.ImageFsInfoRequest.SerializeToString,
        response_deserializer=api__pb2.ImageFsInfoResponse.FromString,
        )


class ImageServiceServicer(object):
  """ImageService defines the public APIs for managing images.
  """

  def ListImages(self, request, context):
    """ListImages lists existing images.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

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


def add_ImageServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'ListImages': grpc.unary_unary_rpc_method_handler(
          servicer.ListImages,
          request_deserializer=api__pb2.ListImagesRequest.FromString,
          response_serializer=api__pb2.ListImagesResponse.SerializeToString,
      ),
      'ImageStatus': grpc.unary_unary_rpc_method_handler(
          servicer.ImageStatus,
          request_deserializer=api__pb2.ImageStatusRequest.FromString,
          response_serializer=api__pb2.ImageStatusResponse.SerializeToString,
      ),
      'PullImage': grpc.unary_unary_rpc_method_handler(
          servicer.PullImage,
          request_deserializer=api__pb2.PullImageRequest.FromString,
          response_serializer=api__pb2.PullImageResponse.SerializeToString,
      ),
      'RemoveImage': grpc.unary_unary_rpc_method_handler(
          servicer.RemoveImage,
          request_deserializer=api__pb2.RemoveImageRequest.FromString,
          response_serializer=api__pb2.RemoveImageResponse.SerializeToString,
      ),
      'ImageFsInfo': grpc.unary_unary_rpc_method_handler(
          servicer.ImageFsInfo,
          request_deserializer=api__pb2.ImageFsInfoRequest.FromString,
          response_serializer=api__pb2.ImageFsInfoResponse.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'runtime.v1alpha2.ImageService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
