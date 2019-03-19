# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=too-many-lines
"""Container Plugin Utility Module"""
import hashlib
import platform
import tarfile
from peewee import SQL
from .models import ContainerImage, ContainerLayer
from .image_ref import add_idpref


class ContainerUtil: # pylint: disable=too-many-instance-attributes
    """Container Utilities"""
    @staticmethod
    def get_additional_time_downlaod(size: int) -> int:
        """Get additional time to downlload something"""
        return size // 5000000

    @staticmethod
    async def reset_docker_info_of_node(uuid_hex: str):
        """ Delete all (local) layers and images from database """
        for image in list(ContainerImage.select(ContainerImage.hash_id,
                                                ContainerImage.available_at)):
            if uuid_hex in image.available_at:
                image.unset_available_at(uuid_hex)
                image.save()

        for layer in list(ContainerLayer.select(ContainerLayer.id,
                                                ContainerLayer.digest,
                                                ContainerLayer.available_at)):
            if uuid_hex in layer.available_at:
                layer.unset_available_at(uuid_hex)
                layer.save()

        await ContainerUtil.delete_unavailable_objects()

    @staticmethod
    async def delete_unavailable_objects():
        """Delete unavailable layers and images"""
        ContainerImage.delete().where(SQL('available_at = \'[]\' AND' \
            ' download_progress = \'null\'')).execute()
        ContainerLayer.delete().where(SQL('available_at = \'[]\' AND ' \
            'download_progress = \'null\'')).execute()

    @staticmethod
    async def get_go_python_arch()-> str:
        """
        In order to compare architecture name of the image (runtime.GOARCH), convert
        platform.machine() and return it.
        """
        arch = platform.machine()

        go_python_arch_mapping = {
            'x86_64': 'amd64',  # linux amd64
            'AMD64' : 'amd64',  # windows amd64

            # TODO
        }
        return go_python_arch_mapping[arch]

    @staticmethod
    async def get_go_python_os()-> str:
        """
        In order to compare OS name of the image (runtime.GOOS), convert
        platform.machine() and return it.
        """
        os_name = platform.system()

        # go_python_os_mapping = {
        #     'Linux': 'linux',
        #     'Windows' : 'windows',
        #     'Darwin' : 'darwin',
        #     # TODO
        # }
        # return go_python_os_mapping[os_name]

        return os_name.lower() # I don't know if this is the right way

    @staticmethod
    def get_diff_size(tar_path: str) -> int:
        """Get the total size of files in a tarball"""
        total = 0
        with tarfile.open(tar_path, 'r:') as tar:
            for tarinfo in tar:
                if tarinfo.isreg():
                    total += tarinfo.size
        return total

    @staticmethod
    def calc_chain_id(parent_chain_id: str, diff_id: str) -> str:
        """calculate chain id"""
        string = parent_chain_id + ' ' + diff_id
        return add_idpref(hashlib.sha256(string.encode('utf-8')).hexdigest())
