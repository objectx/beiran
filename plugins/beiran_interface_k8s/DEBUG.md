How to debug gRPC server
===

Debugging with `crictl`.


#### Install crictl

Install the command referencing [https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md](https://github.com/kubernetes-incubator/cri-tools/blob/master/docs/crictl.md)


### Run beirand


```
$ python -m beirand
```


### Debug

Create `crictl.yaml`, which is a configuration file of `crictl`.

```
$ vim crictl.yaml
```

```
runtime-endpoint: unix:///var/run/beiran-cri.sock
image-endpoint: unix:///var/run/beiran-cri.sock
timeout: 10
debug: true
```

Copy the file to `/etc`

```
$ cp crictl.yaml /etc/
```


Run `crictl`.

```
$ sudo crictl images
DEBU[0000] ListImagesRequest: &ListImagesRequest{Filter:&ImageFilter{Image:&ImageSpec{Image:,},},} 
DEBU[0000] ListImagesResponse: &ListImagesResponse{Images:[&Image{Id:sha256:f06a5773f01e1f77eb4487acb3333649716f45b3c32aad038765dc0ab0337bd4,RepoTags:[redis:latest],RepoDigests:[redis@sha256:096cff9e6024603decb2915ea3e501c63c5bb241e1b56830a52acfd488873843],Size_:83394280,Uid:nil,Username:,} &Image{Id:sha256:29376b8df2ad006b998f5c270b813deee41459e7eafb1ff01dfd78b4d1be0dac,RepoTags:[redis:5.0-rc],RepoDigests:[redis@sha256:61e089bc75e6bd6650a63d8962e3601698115fee26ada4ff1b166b37bf7a7153],Size_:94278870,Uid:nil,Username:,} &Image{Id:sha256:8b89e48b5f157d9455c963b57c85d21e2337c58b8c983bc06f88476610adc129,RepoTags:[nginx:latest],RepoDigests:[nginx@sha256:4a5573037f358b6cdfa2f3e8a9c33a5cf11bcd1675ca72ca76fbe5bd77d0d682],Size_:108970941,Uid:nil,Username:,} &Image{Id:sha256:34f48cd3b7ba1e78329daa435440fb3bedcd78b9de1021ddd9e6d421af8b8efb,RepoTags:[docker.elastic.co/beats/filebeat:6.3.1],RepoDigests:[docker.elastic.co/beats/filebeat@sha256:339ffde106ae930b00afd9fb9feb91fc9643de8257df9c68b4bc1a88ecf5e2f2],Size_:318243701,Uid:nil,Username:filebeat,} &Image{Id:sha256:1bfead9ff707c6e835823e3774257fc95af91a8a342bc498c252c524bfca3626,RepoTags:[grafana/grafana:latest],RepoDigests:[grafana/grafana@sha256:104f434d47c8830be44560edc012c31114a104301cdb81bad6e8abc52a2304f9],Size_:245293540,Uid:nil,Username:grafana,}],} 
IMAGE                              TAG                 IMAGE ID            SIZE
docker.elastic.co/beats/filebeat   6.3.1               34f48cd3b7ba1       318MB
grafana/grafana                    latest              1bfead9ff707c       245MB
nginx                              latest              8b89e48b5f157       109MB
redis                              5.0-rc              29376b8df2ad0       94.3MB
redis                              latest              f06a5773f01e1       83.4MB
```

