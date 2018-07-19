How to debug gRPC server
===

Debugging with `crictl`.


# Install `crictl`

Install the command referencing [https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md](https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md)


# Run beirand and grpc_server.py


```
$ python -m beirand
```


```
$ cd beiran/plugins/beiran_interface_k8s
$ python grpc_server.py
```


# Debug

Create `crictl.yaml`, which is a configure file of `crictl`.

```
$ vim crictl.yaml
```

```
runtime-endpoint: <path-to-repository>/beiran/plugins/beiran_interface_k8s/grpc.sock
image-endpoint: <path-to-repository>/beiran/plugins/beiran_interface_k8s/grpc.sock
timeout: 10
debug: true
```

Copy the file to `/etc`

```
$ cp crictl.yaml /etc/
```


Run `crictl`.

```
$ crictl images
DEBU[0000] ListImagesRequest: &ListImagesRequest{Filter:&ImageFilter{Image:&ImageSpec{Image:,},},} 
DEBU[0000] ListImagesResponse: &ListImagesResponse{Images:[&Image{Id:sha256:f06a5773f01e1f77eb4487acb3333649716f45b3c32aad038765dc0ab0337bd4,RepoTags:[redis:latest],RepoDigests:[],Size_:83394280,Uid:&Int64Value{Value:1,},Username:,} &Image{Id:sha256:29376b8df2ad006b998f5c270b813deee41459e7eafb1ff01dfd78b4d1be0dac,RepoTags:[redis:5.0-rc],RepoDigests:[],Size_:94278870,Uid:&Int64Value{Value:1,},Username:,} &Image{Id:sha256:649dcb69b782d4e281c92ed2918a21fa63322a6605017e295ea75907c84f4d1e,RepoTags:[nginx:latest],RepoDigests:[],Size_:108994719,Uid:&Int64Value{Value:1,},Username:,} &Image{Id:sha256:34f48cd3b7ba1e78329daa435440fb3bedcd78b9de1021ddd9e6d421af8b8efb,RepoTags:[docker.elastic.co/beats/filebeat:6.3.1],RepoDigests:[],Size_:318243701,Uid:&Int64Value{Value:1,},Username:,} &Image{Id:sha256:113a43faa1382a7404681f1b9af2f0d70b182c569aab71db497e33fa59ed87e6,RepoTags:[ubuntu:latest],RepoDigests:[],Size_:81150612,Uid:&Int64Value{Value:1,},Username:,} &Image{Id:sha256:da86e6ba6ca197bf6bc5e9d900febd906b133eaa4750e6bed647b0fbe50ed43e,RepoTags:[k8s.gcr.io/pause:3.1],RepoDigests:[],Size_:742472,Uid:&Int64Value{Value:1,},Username:,}],} 
IMAGE                              TAG                 IMAGE ID            SIZE
docker.elastic.co/beats/filebeat   6.3.1               34f48cd3b7ba1       318MB
k8s.gcr.io/pause                   3.1                 da86e6ba6ca19       742kB
nginx                              latest              649dcb69b782d       109MB
redis                              5.0-rc              29376b8df2ad0       94.3MB
redis                              latest              f06a5773f01e1       83.4MB
ubuntu                             latest              113a43faa1382       81.2MB
```

