import os
import json
import tarfile


def docker_sha_summary(sha):
    """
    shorten sha to 12 bytes length str as docker uses

    e.g "sha256:53478ce18e19304e6e57c37c86ec0e7aa0abfe56dff7c6886ebd71684df7da25" to "53478ce18e19"

    Args:
        sha (string): sha string

    Returns:
        string

    """
    return sha.split(":")[1][0:12]


def docker_find_layer_dir_by_sha(sha):
    """
    try to find local layer directory containing tar archive contents pulled from remote repository

    Args:
        sha (string): sha string

    Returns:
        string directory path or None

    """

    local_diff_dir = '/var/lib/docker/image/overlay2/distribution/v2metadata-by-diffid/sha256'
    local_cache_id = '/var/lib/docker/image/overlay2/layerdb/sha256/{diff_file_name}/cache-id'
    local_layer_dir = '/var/lib/docker/overlay2/{layer_dir_name}/diff/'

    for file_name in os.listdir(local_diff_dir):
        # f_path = f'{local_diff_dir}/{file_name}'  # python 3.5 does not support f strings.
        f_path = '{}/{}'.format(local_diff_dir, file_name)
        f = open(f_path)
        try:
            ff = json.load(f)
            if not ff[0].get('Digest', None) == sha:
                continue  # next file

            f.close()

            with open(local_cache_id.format(diff_file_name=file_name)) as f:
                return local_layer_dir.format(layer_dir_name=f.read())

        except:
            """Pass json load error"""
            pass


def create_tar_archive(dir_path, output_file_path):
    """
    create a tar archive from given path

    Args:
        dir_path (string): directory path to be tarred!

    Returns:


    """
    with tarfile.open(output_file_path, "w") as tar:
        tar.add(dir_path, arcname='.')
