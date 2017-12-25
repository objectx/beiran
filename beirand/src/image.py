import docker
# import os

# def getSize(filename):
#     st = os.stat(filename)
#     return st.st_size
#
# def exists(path):
#     """Test whether a path exists.  Returns False for broken symbolic links"""
#     try:
#         st = os.stat(path)
#     except os.error:
#         return False
#     return True

client = docker.from_env()
image_list = client.images.list()

# driver = client.info().get('Driver')
# print("Docker INFO")
# print("Driver:" + driver)
# print("=================================")
print("IMAGE LIST")
print("=================================")

for i in image_list:
    if len(i.tags) > 0:
        print("Image Name: " + i.tags[0])
    else:
        print("Image has no name")
    print("Image ID:", i.id[7:], "ENC:", i.id[:6])
    print("Size:", i.attrs.get('Size'))
    print("All Tags:")
    print(i.tags)
    print("Layers: ")
    docker_layers = i.attrs.get("RootFS").get("Layers")
    for layer in docker_layers:
        enc = layer[:6]
        layer_id = layer[7:]
        # file = "/var/lib/docker/image/overlay2/layerdb/" + enc + "/" + layer_id
        # if exists(file):
        #     print("ID:", layer_id, "Size:", getSize(file))
        # else:
        #     print("ID:", layer_id, "NOSIZE")
        print("ID:", layer_id, "ENC:", enc)
    print("======================================================")
