### API

I was thinking of also following docker daemon api conventions, but it looks stupid.
( https://docs.docker.com/engine/api/v1.24/#32-images )

```
GET /images[?scope=<local|cluster|origin>][?search=keyword]
GET /images/{imagename}[/info]
GET /images/{imagename}/versions[?scope=<local|cluster|origin>]
GET /images/{imagename}/versions/{tag|hash}/package.tar[.gz|.xz]
GET /images/{imagename}/versions/{tag|hash}/layers

GET /layers/{layer}[/info]
GET /layers/{layer}.tar[.gz|.xz]

GET /nodes
GET /nodes/{uuid}
GET /nodes/{uuid}/images

json: {"type":"pull","url":"docker://nginx:latest","name":"nginx","tag":"latest"} => POST /images
 -- receive task info payload --

json: {"type":"upload","name":"nginx","tag":"latest"} => POST /images
 -- receive task info payload --

stat --printf=%s image.tar | PUT /tasks/{task-uuid}/upload/size
cat image.tar | PUT /tasks/{task-uuid}/upload/stream
..or
docker inspect -f '{{.Size}}' ${IMAGE} | PUT /tasks/{task-uuid}/upload/size
docker save ${IMAGE} | PUT /tasks/{task-uuid}/upload/stream


GET /tasks
GET /tasks/{task-uuid}
GET /tasks/{task-uuid}/status
 -- receive long-polling json-stream for task status --

WS /tasks
 -- receive continous stream of all changes, events of tasks --
```


### Desired Client Behavior;

```
$ beiran images
--- lists local images ----

$ beiran images --available
or
$ beiran images --all
--- lists all images between connected peers ---


$ beiran pull image docker://nginx:latest
( we can follow the convention rkt people made here )
```







### Client Process Interruption

```
$ beiran pull nginx:latest
Downloading ... 35%
..
^C

$ beiran pull nginx:latest
Downloading ... 35%
^C

...
...
...
^C
```
