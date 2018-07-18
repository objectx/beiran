How to debug gRPC server
===

Debugging with `crictl`.


# Install `crictl`

Install the command referencing [https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md](https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md)


# Run grpc_server.py

```
$ cd beiran/plugins/beiran_interface_k8s
$ python grpc_server.py
```

# Create a unix socket

```
$ cd beiran/plugins/beiran_interface_k8s
$ socat -v unix-listen:proxysocket,reuseaddr,fork tcp-connect:localhost:50051
```

# Debug

Create `crictl.yaml`, which is a configure file of `crictl`.

```
$ vim crictl.yaml
```

```
runtime-endpoint: <path-to-proxysocket>
image-endpoint:  <path-to-proxysocket>
timeout: 10
debug: true
```

Then copy the file to `/etc`

```
$ cp crictl.yaml /etc/
```


Run `crictl`.

```
$ crictl images
DEBU[0000] ListImagesRequest: &ListImagesRequest{Filter:&ImageFilter{Image:&ImageSpec{Image:,},},} 
DEBU[0000] ListImagesResponse: &ListImagesResponse{Images:[&Image{Id:hello1,RepoTags:[hello2 hello3],RepoDigests:[deadbeefdeadbeef deadbeef],Size_:4873483,Uid:&Int64Value{Value:1,},Username:hellodesu,}],} 
IMAGE               TAG                 IMAGE ID            SIZE
errorRepoTag        errorRepoTag        hello1              4.87MB
errorRepoTag        errorRepoTag        hello1              4.87MB
$
```

